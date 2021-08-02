# -*- coding: utf-8 -*-
"""Process independent stream handler."""

from multiprocessing import Process, Queue, Event
from sounddevice import Stream, OutputStream,\
    InputStream, CallbackStop, _InputOutputPair
from typing import List, Type
from numpy import zeros, ndarray
from realtimesound._buffer import _MemoryBuffer
import atexit


_buffer = _MemoryBuffer(0, 0, 0)  # placeholder


class _Streamer(Process):
    """Base class for audio streaming based on SoundDevice/PortAudio."""

    def __init__(self, device: _InputOutputPair,
                 samplerate: int,
                 inputs: List[int],
                 outputs: List[int],
                 blocksize: int = 256,
                 block: bool = True,
                 running: Event = None,
                 monitorQ: Queue = None,
                 _has_monitor: Event = None):
        super().__init__(None)
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.device = device
        self.inputs = list(inputs)
        self.inputs.sort()
        self.outputs = list(outputs)
        self.outputs.sort()
        self._statuses: List[str] = []
        self.bufferQ = Queue()
        self.monitorQ = monitorQ
        self.finished = Event()
        self.running = running
        self.block = block
        self._has_monitor = _has_monitor
        self.idx = 0
        return

    @property
    def channels(self):
        return [len(self.inputs), len(self.outputs)]

    def run(self):
        with self._streamType(self.samplerate, self.blocksize,
                              self.device, self._streamNumChannels,
                              'float32', 'low', None,
                              self._callback, self._finished_streaming):
            self.running.set()
            self.finished.wait()
        return

    def start_streaming(self):
        self.start()
        self.running.wait()
        if self.block:
            self.finished.wait()
        return

    def _process_output_data(self, outdata, frames) -> int:
        playframes = (frames if (frames + self.idx) <= self.durationSamples
                      else self.durationSamples - self.idx)
        outdata[:playframes, self.outputs] = self.playdata[self.idx:self.idx + playframes, :]
        outdata[playframes:].fill(0)
        return playframes, outdata.copy()

    def _process_input_data(self, indata, frames) -> int:
        recframes = (frames if (frames + self.idx) <= self.durationSamples
                     else self.durationSamples - self.idx)
        data = indata[:recframes, self.inputs]
        self.bufferQ.put_nowait([data])
        return recframes, data

    def _end_of_callback(self, myframes, cbframes, status, *data):
        if self._has_monitor.is_set():
            self.monitorQ.put_nowait(data)
        if status:
            self._statuses.append(status)
        if myframes < cbframes:
            raise CallbackStop
        return

    def _finished_streaming(self):
        self.running.clear()
        self.finished.set()
        return


class _Player(_Streamer):
    """Player class."""

    def __init__(self, data: ndarray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durationSamples = data.shape[0]
        self.playdata = data.copy()
        self._streamNumChannels = self.outputs[-1] + 1
        self._streamType = OutputStream
        return

    def _callback(self, outdata, frames, time, status):
        playframes, playdata = self._process_output_data(outdata, frames)
        self.idx += playframes
        self._end_of_callback(playframes, frames, status, playdata)
        return


class _Recorder(_Streamer):
    """Recorder class."""

    def __init__(self, tlen: float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durationSamples = round(self.samplerate * tlen + 0.5)
        self._buffer = zeros((self.durationSamples,
                              self.channels[0]), dtype='float32')
        self._streamNumChannels = self.inputs[-1] + 1
        self._streamType = InputStream
        _start_buffer(self._buffer, self.bufferQ, self.running)
        return

    def _callback(self, indata, frames, time, status):
        recframes, recdata = self._process_input_data(indata, frames)
        self.idx += recframes
        self._end_of_callback(recframes, frames, status, recdata)
        return


class _PlaybackRecorder(_Streamer):
    """PlaybackRecorder class."""

    def __init__(self, data: ndarray, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.durationSamples = data.shape[0]
        self.playdata = data.copy()
        self._buffer = zeros((self.durationSamples,
                              self.channels[0]), dtype='float32')
        self._streamNumChannels = [self.inputs[-1] + 1,
                                   self.outputs[-1] + 1]
        self._streamType = Stream
        _start_buffer(self._buffer, self.bufferQ, self.running)
        return

    def _callback(self, indata, outdata, frames, time, status):
        playframes, playdata = self._process_output_data(outdata, frames)
        recframes, recdata = self._process_input_data(indata, frames)
        sframes = max(playframes, recframes)
        self.idx += sframes
        self._end_of_callback(sframes, frames, status, recdata, playdata)
        return


def _start_buffer(buffer, Q, running):
    global _buffer
    _buffer = _MemoryBuffer(buffer, Q, running)
    _buffer.start()
    return


def _buffer_cleanup():
    global _buffer
    if _buffer.is_alive():
        while not _buffer.q.empty():
            _ = _buffer.q.get_nowait()
    return


atexit.register(_buffer_cleanup)
