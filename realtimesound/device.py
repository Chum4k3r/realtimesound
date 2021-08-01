# -*- coding: utf-8 -*-
"""Audio input and output device."""

from sounddevice import Stream, OutputStream,\
    InputStream, _InputOutputPair as IOPair,\
    check_input_settings, check_output_settings
from typing import List
from numpy import ndarray
from multiprocessing import Event
from realtimesound._streamer import _Streamer
from realtimesound.monitor import Monitor
import atexit


_monitor = Monitor(1, 0, 0, 0, 0, 0)  # placeholder
_streamer = _Streamer((0, 0), 0, [0], [0], 0, 0)  # placeholder


class Device(object):
    """Audio device object abstraction."""

    def __init__(self, hostapi: object,
                 id: IOPair,
                 device_data: IOPair,
                 samplerate: int = None,
                 inputs: List[int] = None,
                 outputs: List[int] = None):
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
        self._hostapi = hostapi
        self._data = device_data
        self._samplerate = samplerate
        self._inputs = inputs
        self._outputs = outputs
        self._has_monitor = Event()
        return

    @property
    def id(self) -> IOPair:
        """Device input and output IDs."""
        return self._id

    @property
    def samplerate(self) -> int:
        """Device sampling rate."""
        return self._samplerate

    @samplerate.setter
    def samplerate(self, fs):
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
        return self._hostapi

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
        self._has_monitor.clear()
        if MonitorSub is not None and issubclass(MonitorSub, Monitor):
            self._has_monitor.set()
        self._MonitorSub = MonitorSub
        self._MonitorArgs = args
        self._MonitorKWargs = kwargs
        return

    def play(self, data: ndarray, *,
             block: bool = True):
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
        _streamer_cleanup()
        _streamer = _setup_streamer(self, block)
        if self._has_monitor.is_set():
            _monitor_cleanup()
            _start_monitor(self._MonitorSub, self._MonitorArgs,
                           self._MonitorKWargs, self.samplerate, self.channels[1],
                           _streamer.running, _streamer.monitorQ)
        _streamer._start_stream(OutputStream, data)
        return

    def record(self, tlen: float, *,
               block: bool = True) -> ndarray:
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
        _streamer_cleanup()
        _streamer = _setup_streamer(self, block)
        if self._has_monitor.is_set():
            _monitor_cleanup()
            _start_monitor(self._MonitorSub, self._MonitorArgs,
                           self._MonitorKWargs, self.samplerate, self.channels[0],
                           _streamer.running, _streamer.monitorQ)
        _streamer._start_stream(InputStream, tlen)
        return _streamer._buffer.copy() if block else _streamer._buffer

    def playrec(self, data: ndarray, *,
                block: bool = True) -> ndarray:
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
        _streamer_cleanup()
        _streamer = _setup_streamer(self, block)
        if self._has_monitor.is_set():
            _monitor_cleanup()
            _start_monitor(self._MonitorSub, self._MonitorArgs,
                           self._MonitorKWargs, self.samplerate, self.channels,
                           _streamer.running, _streamer.monitorQ)
        _streamer._start_stream(Stream, data)
        return _streamer._buffer.copy() if block else _streamer._buffer


def _start_monitor(MonitorSub, MonitorInitArgs, MonitorInitKWargs,
                   samplerate, channels, running, Q):
    global _monitor
    _monitor = MonitorSub(*MonitorInitArgs,
                          **MonitorInitKWargs,
                          samplerate=samplerate,
                          numChannels=channels,
                          running=running,
                          q=Q)
    _monitor.start()
    return


def _monitor_cleanup():
    global _monitor
    if _monitor.is_alive():
        while not _monitor.q.empty():
            _ = _monitor.q.get_nowait()
        _monitor.join(timeout=5.)
    _monitor.close()
    return


atexit.register(_monitor_cleanup)


def _setup_streamer(dev, block: bool):
    global _streamer
    _streamer = _Streamer(dev.id, dev.samplerate, dev.inputs,
                          dev.outputs, block=block, _has_monitor=dev._has_monitor)
    return _streamer


def _streamer_cleanup():
    global _streamer
    if _streamer.is_alive():
        while not _streamer.monitorQ.empty():
            _ = _streamer.monitorQ.get_nowait()
        while not _streamer.bufferQ.empty():
            _ = _streamer.monitorQ.get_nowait()
        _streamer.join(timeout=_streamer.durationSamples/_streamer.samplerate)
    _streamer.close()
    return


atexit.register(_streamer_cleanup)
