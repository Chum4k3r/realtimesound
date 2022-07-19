# -*- coding: utf-8 -*-
"""Record buffering thread."""

from multiprocessing import Event, Queue

from numpy import ndarray, zeros
from realtimesound.audio import AudioGenerator, AudioReceiver
from threading import Thread
from queue import Empty
from numpy.core.shape_base import vstack


class Source(Thread):
    """Thread that feed output audio data."""

    have_generator = Event()

    def __init__(self, generator: AudioGenerator, q: Queue, running: Event):
        super().__init__(name='SourceThread')
        self.q = q
        self.running = running
        self.generator = generator
        return

    def replace_generator_data(self, audio: ndarray):
        self.generator.emplace_audio(audio)
        self.have_generator.set()
        return

    def run(self):
        """Send streamer playback data."""
        self.running.wait()
        while True:
            try:
                if self.have_generator.is_set():
                    self.q.put_nowait(self.generator.next_audio_block())
            except StopIteration:
                if not self.running.is_set():
                    break
                self.q.put_nowait(zeros(self.generator.size, self.generator.channels))                
                self.have_generator.clear()            
        return


class Sink(Thread):
    """Thread that retrieve input audio data."""

    have_receiver = Event()

    def __init__(self, receiver: AudioReceiver, q: Queue, running: Event):
        super().__init__(name='SinkThread')
        self.running = running
        self.q = q
        self.receiver = receiver
        return

    def replace_receiver_buffer(self, size: int):
        self.receiver.emplace_size(size)
        self.have_receiver.set()
        return

    def run(self):
        """Save streamer recorded data."""
        self.running.wait(5.)
        while True:
            try:
                if self.have_receiver.is_set():
                    self.receiver.next_audio_block(self.q.get(timeout=2.))
                else:
                    self.have_receiver.wait()
            except StopIteration:
                self.have_receiver.clear()
            except Empty:
                if not self.running.is_set():
                    break                
        return


class FileSink(Sink):
    def __init__(self, durationSamples: int, samplingRate: int,
                 numChannels: int, q: Queue):
        super().__init__(self, durationSamples, samplingRate, numChannels, q)
        return
