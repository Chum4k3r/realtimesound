# -*- coding: utf-8 -*-
"""Record buffering thread."""

from multiprocessing import Event, Queue
from threading import Thread
from queue import Empty
from numpy import ndarray


class _MemoryBuffer(Thread):
    """Helper class to retrieve input audio data."""

    def __init__(self, buffer: ndarray, q: Queue, running: Event):
        super().__init__(None)
        self.running = running
        self.buffer = buffer
        self.idx = 0
        self.q = q
        return

    def run(self):
        """Save streamer recorded data."""
        self.running.wait(5.)
        while True:
            try:
                data, = self.q.get(1.)
                shift = len(data)
                self.buffer[self.idx:self.idx + shift] = data
                self.idx += shift
            except Empty:
                if not self.running.is_set():
                    break
        return


class _FileBuffer(_MemoryBuffer):
    def __init__(self, durationSamples: int, samplingRate: int,
                 numChannels: int, q: Queue):
        super().__init__(self, durationSamples, samplingRate, numChannels, q)
        return
