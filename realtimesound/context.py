from queue import Empty
from realtimesound.audio import AudioGenerator, AudioReceiver
from typing import Union
from numpy import ceil, ndarray
from multiprocessing import Event, Queue
from realtimesound.device import Device
from realtimesound.buffer import Source, Sink
from realtimesound.streams.streamer import Streamer, Player, Recorder,\
    PlaybackRecorder, ContinuousStreamer
from realtimesound.monitor import Monitor, MonitorThread, MonitorProcess
import atexit


class RealTimeContext:
    """The one handler to rule them all."""

    _monitor: MonitorThread
    _streamer: ContinuousStreamer
    _source: Source
    _sink: Sink

    _MonitorSub: Monitor
    _MonitorArgs: tuple()
    _MonitorKWargs: dict()

    def __init__(self, device: Device):
        self._device = device
        self._online = Event()
        self._has_monitor = Event()
        self._extern_monitor = Event()
        self._running = Event()
        self._stop_requested = Event()
        self._monitorQ = Queue()
        self._sourceQ = Queue()
        self._sinkQ = Queue()
        return

    @property
    def device(self) -> Device:
        """Device configuration."""
        return self._device

    def plug_monitor(self, MonitorSub: Monitor,
                     args: tuple = (),
                     kwargs: dict = {}) -> bool:
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
        bool.
            False if MonitorSub is None, else True

        """
        if not self._online.is_set():
            self._has_monitor.clear()
            self._extern_monitor.clear()
            if MonitorSub and issubclass(MonitorSub, Monitor):
                self._has_monitor.set()
            self._MonitorSub = MonitorSub
            self._MonitorArgs = args
            self._MonitorKWargs = kwargs
        return self._has_monitor.is_set()

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

    def open_stream(self):
        """Turn on the continuous streaming mode."""
        self._online.set()
        self._start_sink_and_source()
        self._setup_streamer(ContinuousStreamer, block=False)
        if self._has_monitor.is_set() and not self._extern_monitor.is_set():
            self._start_monitor()
        self._streamer.start_streaming()
        pass

    def close_stream(self):
        """Turn off the continuous streaming mode."""
        self._stop_requested.set()
        if self._has_monitor.is_set() and not self._extern_monitor.is_set():
            self._monitor_cleanup()
        self._sink_and_source_cleanup()
        self._online.clear()
        return

    def _setup_streamer(self, streamerType: type[Streamer], block: bool):
        self._streamer = streamerType(self.device.id, self.device.samplerate,
                                      self.device.inputs, self.device.outputs,
                                      self._sourceQ, self._sinkQ, self._stop_requested,
                                      128, block=block, running=self._running,
                                      monitorQ=self._monitorQ, _has_monitor=self._has_monitor)
        return

    def _start_sink_and_source(self):
        self._sink = Sink(self.device.channels['input'], self._sinkQ, self._running)
        self._source = Source(self.device.channels['output'], self._sourceQ, self._running)
        self._sink.start()
        self._source.start()
        return

    def _sink_and_source_cleanup(self):
        try:
            if self._sink.is_alive():
                while not self._sink.q.empty():
                    try:
                        _ = self._sink.q.get_nowait()
                    except Empty:
                        pass
                self._sink.join(timeout=5.)
            if self._source.is_alive():
                while not self._source.q.empty():
                    try:
                        _ = self._source.q.get_nowait()
                    except Empty:
                        pass
                self._source.join(timeout=5.)
        except ValueError:
            pass
        return

    def _start_monitor(self):
        self._monitor = self._MonitorSub(*self._MonitorArgs,
                                         **self._MonitorKWargs,
                                         samplerate=self.device.samplerate,
                                         numChannels=self.device.channels,
                                         running=self._running,
                                         q=self._monitorQ)
        self._monitor.start()
        return

    def _monitor_cleanup(self):
        try:
            if self._monitor.is_alive():
                while not self._monitor.q.empty():
                    try:
                        _ = self._monitor.q.get_nowait()
                    except Empty:
                        pass
                self._monitor.join(timeout=5.)
            if issubclass(type(self._monitor), MonitorProcess):
                    self._monitor.close()
        except ValueError:
            pass
        return

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
        if self._online.is_set():
            # block = False
            self._source.place_generator(AudioGenerator(data))

            if block == True:
                self._streamer.finished.wait()
        # else:
            # _streamer_cleanup()
            # _streamer = _setup_streamer(Player, self, data, block)
            # if self._has_monitor.is_set() and not self._extern_monitor.is_set():
            #     _monitor_cleanup()
            #     _start_monitor(self, self.device.channels[1])
            #     # Timer(1.1*(data.shape[0]/self.samplerate), _monitor_cleanup).start()
            # _streamer.start_streaming()
            # # Timer(1.1*(data.shape[0]/self.samplerate), _streamer_cleanup).start()
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
        if self._online.is_set():
            # block = False
            self._sink.place_receiver(AudioReceiver(self.device.channels['input'], int(tlen*self.device.samplerate)))

            if block == True:
                self._streamer.finished.wait()
        # else:
        #     _streamer_cleanup()
        #     _streamer = _setup_streamer(Recorder, self, tlen, block)
        #     if self._has_monitor.is_set() and not self._extern_monitor.is_set():
        #         _monitor_cleanup()
        #         _start_monitor(self, self.channels[0])
        #         # Timer(1.1*(tlen), _monitor_cleanup).start()
        #     _streamer.start_streaming()
        #     # Timer(1.1*(tlen), _streamer_cleanup).start()
        return  # _streamer._buffer.copy() if block else _streamer._buffer

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
        # global _streamer
        if self._online.is_set():
            # block = False               # TODO: Source e Sink
            self._playQ.put(data)
            # _streamer._new_recdata(data.shape[0]/self.samplerate)
            # do online stuff
            if block == True:
                self._streamer.finished.wait()
        # else:
        #     _streamer_cleanup()
        #     _streamer = _setup_streamer(PlaybackRecorder, self, data, block)
        #     if self._has_monitor.is_set() and not self._extern_monitor.is_set():
        #         _monitor_cleanup()
        #         _start_monitor(self, self.channels)
        #         # Timer(1.1*(data.shape[0]/self.samplerate), _monitor_cleanup).start()
        #     _streamer.start_streaming()
        #     # Timer(1.1*(data.shape[0]/self.samplerate), _streamer_cleanup).start()
        # return _streamer._buffer.copy() if block else _streamer._buffer


    # def _streamer_cleanup(self):
    #     try:
    #         if self._streamer.is_alive():
    #             while not self._streamer.monitorQ.empty():
    #                 try:
    #                     _ = self._streamer.monitorQ.get_nowait()
    #                 except Empty:
    #                     pass
    #             while not self._streamer.bufferQ.empty():
    #                 try:
    #                     _ = self._streamer.bufferQ.get_nowait()
    #                 except Empty:
    #                     pass
    #             self._streamer.join(timeout=5.)
    #         self._streamer.close()
    #     except ValueError:
    #         pass
    #     return


def create_context(device: Device) -> RealTimeContext:
    ctx = RealTimeContext(device)
    return ctx
