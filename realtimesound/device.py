# -*- coding: utf-8 -*-
"""Audio input and output device."""

from queue import Empty
from sounddevice import _InputOutputPair as IOPair,\
    check_input_settings, check_output_settings
from typing import List, Union
from numpy import ndarray
from multiprocessing import Event, Queue
from threading import Timer
from realtimesound._streamer import _Player, _Recorder,\
    _PlaybackRecorder, _ContinuousStreamer
from realtimesound.monitor import Monitor,\
    MonitorThread, MonitorProcess
import atexit


_monitor = MonitorThread(1, 0, 0, 0, 0, 0)  # placeholder
_streamer = _ContinuousStreamer(0, (0, 0), 0, [0], [0], 0, 0)  # placeholder


class Device(object):
    """Audio device object abstraction."""

    def __init__(self, host: object,
                 id: IOPair,
                 device_data: IOPair,
                 samplerate: int = None,
                 inputs: List[int] = None,
                 outputs: List[int] = None):
        """
        Provide functionality to playback and record audio data.

        Parameters
        ----------
        hostapi : object
            The Host object.
        id : IOPair
            Input and output device id on Host.
        device_data : IOPair
            Input and output device description as dicts.
        samplerate : int, optional
            Amount of samples per second. The default is None.
        inputs : List[int], optional
            List of active input channels. If None, activate all.
            The default is None.
        outputs : List[int], optional
            List of active output channels. If None, activate all.
            The default is None.

        Returns
        -------
        None.

        """
        if samplerate is None:
            samplerate = max(device_data['input']['default_samplerate'],
                             device_data['output']['default_samplerate'])
        if inputs is None:
            inputs = list(range(device_data['input']['max_input_channels']))
        inputs.sort()
        if outputs is None:
            outputs = list(range(device_data['output']['max_output_channels']))
        outputs.sort()
        check_input_settings(id['input'], inputs[-1] + 1, 'float32', None, samplerate)
        check_output_settings(id['output'], outputs[-1] + 1, 'float32', None, samplerate)

        super().__init__()
        self._id = id
        self._host = host
        self._data = device_data
        self._samplerate = samplerate
        self._inputs = inputs
        self._outputs = outputs
        self._has_monitor = Event()
        self._extern_monitor = Event()
        self._running = Event()
        self._monitorQ = Queue()
        self._online = Event()
        self._playQ = Queue()
        return

    @property
    def id(self) -> IOPair:
        """Device input and output unique IDs on system."""
        return self._id

    @property
    def samplerate(self) -> int:
        """Amount of samples per second."""
        return self._samplerate

    @samplerate.setter
    def samplerate(self, fs):
        if not self._online.is_set():
            check_input_settings(self.id['input'], self.inputs[-1] + 1,
                                 'float32', None, fs)
            check_output_settings(self.id['output'], self.outputs[-1] + 1,
                                  'float32', None, fs)
            self._samplerate = int(fs)
        return

    @property
    def inputs(self) -> List[int]:
        """Active input channels."""
        return self._inputs

    @inputs.setter
    def inputs(self, mapping: List[int]):
        if not self._online.is_set():
            if (len(mapping) > self.maxInputs
                    or max(mapping) >= self.maxInputs):
                raise ValueError("Too many channels or unavailable channel number.")
            mapping.sort()
            check_input_settings(self.id['input'], mapping[-1] + 1,
                                 'float32', None, self.samplerate)
            self._inputs.clear()
            self._inputs.extend(mapping)
            self._inputs.sort()
        return

    @property
    def outputs(self) -> List[int]:
        """Active output channels."""
        return self._outputs

    @outputs.setter
    def outputs(self, mapping: List[int]):
        if not self._online.is_set():
            if (len(mapping) > self.maxOutputs
                    or max(mapping) >= self.maxOutputs):
                raise ValueError("Too many channels or unavailable channel number.")
            mapping.sort()
            check_output_settings(self.id['output'], mapping[-1] + 1,
                                  'float32', None, self.samplerate)
            self._outputs.clear()
            self._outputs.extend(mapping)
            self._outputs.sort()
        return

    @property
    def channels(self) -> List[int]:
        """Total active [input, output] channels."""
        return [len(self.inputs), len(self.outputs)]

    @property
    def inputName(self) -> str:
        """Input device name on system."""
        return self._data['input']['name']

    @property
    def outputName(self):
        """Output device name on system."""
        return self._data['output']['name']

    @property
    def host(self):
        """Device's host object."""
        return self._host

    @property
    def maxInputs(self):
        """Maximum input channels."""
        return self._data['input']['max_input_channels']

    @property
    def maxOutputs(self):
        """Maximum output channels."""
        return self._data['output']['max_output_channels']

    @property
    def defaultLowLatency(self):
        """Low latency value for [input, output]."""
        return [self._data['input']['default_low_input_latency'],
                self._data['output']['default_low_Output_latency']]

    @property
    def defaultHighLatency(self):
        """High latency value for [input, output]."""
        return [self._data['input']['default_high_input_latency'],
                self._data['output']['default_high_output_latency']]

    def plug_monitor(self, MonitorSub: Monitor,
                     args: tuple = (),
                     kwargs: dict = {}):
        """
        Connect the `MonitorSub` to be used with the streams.

        The `Monitor` is a `multiprocessing.Process`, thus, it can only be started
        once, requiring that for every run of `play`, `record` or `playrec` a
        new `Monitor` object must be created.

        The `Device` class ensures that every resource is handled properly,
        by asserting the queues are empty and closing every process that
        it has opened.

        Parameters
        ----------
        MonitorSub : Monitor
            Subclass implementation of Monitor.
        args : tuple, optional
            Arguments that must be passed to the `MonitorSub.__init__()` method.
            These arguments will be passed as `__init__(*args)`
            The default is ().
        kwargs: dict, optional
            Arguments that must be passed to the `MonitorSub.__init__()` method.
            These arguments will be passed as `__init__(**kwargs)`
            The default is {}.

        Returns
        -------
        None.

        """
        if not self._online.is_set():
            self._has_monitor.clear()
            self._extern_monitor.clear()
            if MonitorSub is not None and issubclass(MonitorSub, Monitor):
                self._has_monitor.set()
            self._MonitorSub = MonitorSub
            self._MonitorArgs = args
            self._MonitorKWargs = kwargs
        return

    def use_external_monitor(self) -> Union[Queue, Event]:
        """
        Provide access to monitor queue and the stream running state.

        In the case a user want to access the data provided to monitor without
        using the provided framework, this method grants access to the queue
        and the running state of the stream, allowing syncronization.

        Notes
        -----
        If not using the provided `Monitor` implementation, any allocated
        resource must be managed by the extern monitor provider. This includes
        initialization, proper data retrieval, and termination.

        Returns
        -------
        Queue, Event
            The monitor queue used to retrieve data and the running state of
            the stream.

        """
        self._has_monitor.set()
        self._extern_monitor.set()
        return self._monitorQ, self._running

    def play(self, data: ndarray, *, block: bool = True):
        """
        Play `data` as a sound.

        Parameters
        ----------
        data : ndarray
            Array containing the audio samples.
        block : bool, optional
            Wait for stream to end (`True`), or return immediately (`False`).
            The default is True.

        Returns
        -------
        None.

        """
        global _streamer
        if self._online.is_set():
            block = False
            self._playQ.put(data)
        else:
            _streamer_cleanup()
            _streamer = _setup_streamer(_Player, self, data, block)
            if self._has_monitor.is_set() and not self._extern_monitor.is_set():
                _monitor_cleanup()
                _start_monitor(self, self.channels[1])
                # Timer(1.1*(data.shape[0]/self.samplerate), _monitor_cleanup).start()
            _streamer.start_streaming()
            # Timer(1.1*(data.shape[0]/self.samplerate), _streamer_cleanup).start()
        return

    def record(self, tlen: float, *, block: bool = True) -> ndarray:
        """
        Record sound of `tlen` duration.

        Parameters
        ----------
        tlen : float
            Duration of audio record.
        block : bool, optional
            Wait for stream to end (`True`), or return immediately (`False`).
            The default is True.

        Returns
        -------
        ndarray
            Recorded data.

        """
        global _streamer
        if self._online.is_set():
            block = False
            _streamer._new_recdata(tlen)
        else:
            _streamer_cleanup()
            _streamer = _setup_streamer(_Recorder, self, tlen, block)
            if self._has_monitor.is_set() and not self._extern_monitor.is_set():
                _monitor_cleanup()
                _start_monitor(self, self.channels[0])
                # Timer(1.1*(tlen), _monitor_cleanup).start()
            _streamer.start_streaming()
            # Timer(1.1*(tlen), _streamer_cleanup).start()
        return _streamer._buffer.copy() if block else _streamer._buffer

    def playrec(self, data: ndarray, *, block: bool = True) -> ndarray:
        """
        Simultaneously play `data` and record an audio of same duration.

        Parameters
        ----------
        data : ndarray
            Array containing the audio samples.
        block : bool, optional
            Wait for stream to end (`True`), or return immediately (`False`).
            The default is True.

        Returns
        -------
        ndarray
            Recorded data.

        """
        global _streamer
        if self._online.is_set():
            block = False
            self._playQ.put(data)
            _streamer._new_recdata(data.shape[0]/self.samplerate)
            # do online stuff
        else:
            _streamer_cleanup()
            _streamer = _setup_streamer(_PlaybackRecorder, self, data, block)
            if self._has_monitor.is_set() and not self._extern_monitor.is_set():
                _monitor_cleanup()
                _start_monitor(self, self.channels)
                # Timer(1.1*(data.shape[0]/self.samplerate), _monitor_cleanup).start()
            _streamer.start_streaming()
            # Timer(1.1*(data.shape[0]/self.samplerate), _streamer_cleanup).start()
        return _streamer._buffer.copy() if block else _streamer._buffer

    def turn_on(self):
        """Turn on the continuous streaming mode."""
        global _streamer
        self._online.set()
        _streamer = _setup_streamer(_ContinuousStreamer, self,
                                    self._playQ, False)
        if self._has_monitor.is_set() and not self._extern_monitor.is_set():
            _start_monitor(self, self.channels)
        _streamer.start_streaming()
        pass

    def turn_off(self):
        """Turn off the continuous streaming mode."""
        global _streamer
        _streamer.running.clear()
        self._online.clear()
        if self._has_monitor.is_set() and not self._extern_monitor.is_set():
            _monitor_cleanup()
        _streamer_cleanup()
        return


def _start_monitor(dev, channels):
    global _monitor
    _monitor = dev._MonitorSub(*dev._MonitorArgs,
                               **dev._MonitorKWargs,
                               samplerate=dev.samplerate,
                               numChannels=channels,
                               running=dev._running,
                               q=dev._monitorQ)
    _monitor.start()
    return


def _monitor_cleanup():
    global _monitor
    try:
        if _monitor.is_alive():
            while not _monitor.q.empty():
                try:
                    _ = _monitor.q.get_nowait()
                except Empty:
                    pass
            _monitor.join(timeout=5.)
        if issubclass(type(_monitor), MonitorProcess):
                _monitor.close()
    except ValueError:
        pass
    return


atexit.register(_monitor_cleanup)


def _setup_streamer(streamerType, dev, data, block: bool):
    global _streamer
    _streamer = streamerType(data, dev.id, dev.samplerate, dev.inputs,
                             dev.outputs, 256, block=block,
                             running=dev._running, monitorQ=dev._monitorQ,
                             _has_monitor=dev._has_monitor)
    return _streamer


def _streamer_cleanup():
    global _streamer
    try:
        if _streamer.is_alive():
            while not _streamer.monitorQ.empty():
                try:
                    _ = _streamer.monitorQ.get_nowait()
                except Empty:
                    pass
            while not _streamer.bufferQ.empty():
                try:
                    _ = _streamer.bufferQ.get_nowait()
                except Empty:
                    pass
            _streamer.join(timeout=5.)
        _streamer.close()
    except ValueError:
        pass
    return


atexit.register(_streamer_cleanup)
