# -*- coding: utf-8 -*-
"""Process independent stream handler."""

from multiprocessing import Process, Queue, Event, Value
from queue import Empty
from sounddevice import Stream, OutputStream,\
    InputStream, CallbackStop, _InputOutputPair
from typing import List
from numpy import zeros, ndarray
from realtimesound.buffer import Sink


class Streamer(Process):
    """Base class for audio streaming based on SoundDevice/PortAudio."""

    recording = Event()
    playing = Event()
    finished = Event()
    callback_safe = Event()
    statuses: List[str] = []

    def __init__(self, device: _InputOutputPair, # config
                 samplerate: int,  # config
                 inputs: List[int],  # config
                 outputs: List[int],  # config
                 sourceQ: Queue,  # message channel
                 sinkQ: Queue,  # message channel
                 stop_request: Event,  # estado -> requer checagem eventual (hurr durr)
                 blocksize: int,  # config
                 block: bool,  # mode setting -> se block==True, espera o fim da stream antes de retornar 
                 running: Event,
                 monitorQ: Queue,
                 _has_monitor: Event):
        super().__init__(name='StreamerProcess')
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.device = device
        self.inputs = list(inputs)
        self.inputs.sort()
        self.outputs = list(outputs)
        self.outputs.sort()
        self.sourceQ = sourceQ
        self.sinkQ = sinkQ
        self.monitorQ = monitorQ
        self.running = running
        self.stop_request = stop_request
        self.block = block
        self._has_monitor = _has_monitor
        return

    @property
    def channels(self):
        """Active input/output channels count."""
        return [len(self.inputs), len(self.outputs)]

    def start_streaming(self):
        """Start streaming process and wait for it to start. If blocking is set to True, waits untill process finish."""
        self.stop_request.clear()  # evento
        self.start()
        self.running.wait()
        if self.block:
            self.finished.wait()
        return

    def run(self):
        try:
            with Stream(self.samplerate, self.blocksize,
                        self.device, [self.inputs[-1] + 1,
                                    self.outputs[-1] + 1],
                        'float32', 'low', None,
                        self._callback, self._finished_streaming) as self.stream:
                self.running.set()
                self.finished.wait()
        except Exception as e:
            for n in range(20):
                print(self.stream.time, type(e), e)
            pass
        return

    def _callback(self, indata, outdata, frames, time, status):
        # recording section
        recdata, playdata = self._start_of_callback(indata, outdata)
        if self.recording.is_set():
            self.sinkQ.put_nowait(recdata)

        # playback section
        playdata = self.sourceQ.get_nowait()

        # finishing section
        self._end_of_callback(status, [recdata, playdata])
        return

    def _start_of_callback(self, indata, outdata):
        self.callback_safe.clear()
        recdata = indata[:, self.inputs]
        playdata = outdata[:, self.outputs]
        return recdata, playdata

    def _end_of_callback(self, status, *data):
        self.callback_safe.set()
        if self._has_monitor.is_set():
            self.monitorQ.put_nowait(data)
        if status:
            self.statuses.append(status)
        if self.stop_request.is_set():
            raise CallbackStop
        return

    def _finished_streaming(self):
        self.running.clear()
        self.finished.set()
        return

    def _process_output_data(self, outdata, frames) -> int:
        playframes = (frames if (frames + self.idx) <= self.durationSamples
                      else self.durationSamples - self.idx)
        playdata = self.sourceQ.get_nowait()
        outdata.fill(0)
        outdata[:playframes, self.outputs] = playdata
        return playdata.shape[0], playdata

    def _process_input_data(self, indata, frames) -> int:
        recframes = (frames if (frames + self.idx) <= self.durationSamples
                     else self.durationSamples - self.idx)
        recdata = indata[:recframes, self.inputs]
        self.sinkQ.put_nowait([recdata])
        return recframes, recdata


class Player(Streamer):
    """Player class."""

    def __init__(self, data: ndarray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durationSamples = data.shape[0]
        self.playdata = data.copy()
        return

    def run(self):
        with OutputStream(self.samplerate, self.blocksize,
                          self.device, self.outputs[-1] + 1,
                          'float32', 'low', None,
                          self._callback, self._finished_streaming):
            self.running.set()
            self.finished.wait()
        return

    def _callback(self, outdata, frames, time, status):
        playframes, playdata = self._process_output_data(outdata, frames)
        self.idx += playframes
        self._end_of_callback(playframes, frames, status, playdata)
        return


class Recorder(Streamer):
    """Recorder class."""

    def __init__(self, tlen: float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durationSamples = round(self.samplerate * tlen + 0.5)
        self.buffer = zeros((self.durationSamples,
                             self.channels[0]), dtype='float32')
        return

    def run(self):
        with InputStream(self.samplerate, self.blocksize,
                         self.device, self.inputs[-1] + 1,
                         'float32', 'low', None,
                         self._callback, self._finished_streaming):
            self.running.set()
            self.finished.wait()
        return

    def _callback(self, indata, frames, time, status):
        recframes, recdata = self._process_input_data(indata, frames)
        self.idx += recframes
        self._end_of_callback(recframes, frames, status, recdata)
        return


class PlaybackRecorder(Streamer):
    """PlaybackRecorder class."""

    def __init__(self, data: ndarray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durationSamples = data.shape[0]
        self.playdata = data.copy()
        self._buffer = zeros((self.durationSamples,
                              self.channels[0]), dtype='float32')
        self._streamNumChannels = [self.inputs[-1] + 1,
                                   self.outputs[-1] + 1]
        _start_buffer(self._buffer, self.bufferQ, self.running)
        return

    def run(self):
        with Stream(self.samplerate, self.blocksize,
                    self.device, [self.inputs[-1] + 1,
                                  self.outputs[-1] + 1],
                    'float32', 'low', None,
                    self._callback, self._finished_streaming):
            self.running.set()
            self.finished.wait()
        return

    def _callback(self, indata, outdata, frames, time, status):
        playframes, playdata = self._process_output_data(outdata, frames)
        recframes, recdata = self._process_input_data(indata, frames)
        sframes = max(playframes, recframes)
        self.idx += sframes
        self._end_of_callback(sframes, frames, status, recdata, playdata)
        return


class ContinuousStreamer(Streamer):
    """Continuous streaming streamer."""

    def __init__(self, playQ, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._recIdx = Value('i', 0)
        self._recSamples = Value('i', 256)
        self._playIdx = Value('i', 0)
        self._playSamples = Value('i', 256)
        self._playQ = playQ
        self._recording = Event()
        self._callback_safe = Event()
        self.playdata = zeros((self._playSamples.value, self.channels[1]))
        self._buffer = zeros((self._recSamples.value, self.channels[0]))
        self._callback_safe.set()
        return

    def run(self):
        with Stream(self.samplerate, self.blocksize,
                    self.device, [self.inputs[-1] + 1,
                                  self.outputs[-1] + 1],
                    'float32', 'low', None,
                    self._callback, self._finished_streaming) as self.stream:
            self.running.set()
            self.finished.set()
            while self.running.is_set():
                try:
                    playdata = self._playQ.get(timeout=5.)
                except Empty:
                    # no playdata issued
                    continue
                self._new_playdata(playdata)
                self.finished.wait(timeout=self._recSamples.value/self.samplerate + 2.)
        return

    def _new_recdata(self, tlen):
        self._callback_safe.wait()
        self._recSamples.value = int(tlen * self.samplerate + 0.5)
        self._recIdx.value = 0
        self._buffer = zeros((self._recSamples.value, self.channels[0]))
        _start_buffer(self._buffer, self.bufferQ, self._recording)
        self._recording.set()
        return

    def _new_playdata(self, playdata):
        self._callback_safe.wait()
        self._playSamples.value = playdata.shape[0]
        self._playIdx.value = 0
        self.playdata = playdata
        self.finished.clear()
        return

    def _callback(self, indata, outdata, frames, time, status):
        # recording section
        self._callback_safe.clear()
        recdata = indata[:, self.inputs]
        if self._recording.is_set():
            recframes = (frames if (frames + self._recIdx.value) <= self._recSamples.value
                         else self._recSamples.value - self._recIdx.value)
            self.bufferQ.put_nowait([recdata[:recframes]])
            self._recIdx.value += recframes
            if recframes < frames:
                self._recording.clear()

        # playback section
        outdata.fill(0)
        playdata = outdata[:, self.outputs]
        if not self.finished.is_set():
            playframes = (frames if (frames + self._playIdx.value) <= self._playSamples.value
                          else self._playSamples.value - self._playIdx.value)
            playdata[:playframes] = \
                self.playdata[self._playIdx.value:self._playIdx.value + playframes, :]
            outdata[:, self.outputs] = playdata
            self._playIdx.value += playframes
            if playframes < frames:
                self.finished.set()

        # finishing section
        if self._has_monitor.is_set():
            self.monitorQ.put_nowait([recdata, playdata])
        if status:
            self._statuses.append(status)
        self._callback_safe.set()
        return


def _start_buffer(buffer, Q, running):
    global _buffer
    _buffer =  Sink(buffer, Q, running)  # placeholder
    _buffer.start()
    return


def _buffer_cleanup():
    global _buffer
    if _buffer.is_alive():
        while not _buffer.q.empty():
            _ = _buffer.q.get_nowait()
        _buffer.join(timeout=5.)
    return
