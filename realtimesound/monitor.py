# -*- coding: utf-8 -*-
"""Monitor abstract base definition."""

from multiprocessing import Queue, Event, Process
from threading import Thread
from queue import Empty
from numpy import zeros, roll, ndarray
from typing import List
from time import time, sleep


class Monitor(object):
    """Base class for audio stream monitoring."""

    def __init__(self, FPS: int, winsize: int or float,
                 samplerate: int, numChannels: List[int],
                 running: Event, q: Queue):
        """
        Abstraction of an audio monitoring unit.

        It is made for subclassing only, and provide basic interface for
        interaction with objects of `Streamer` subclasses.

        Any subclass of `Monitor` must reimplement the `process_data` method
        and might reimplement the `setup` and `tear_down` methods.

        Parameters
        ----------
        FPS : int
            Frames per second.
        winsize : int or float
            If is int, taken as the buffer number of samples, if it is float,
            the number of samples is calculated by `int(winsize * samplerate + 0.5)`
        samplerate : int
            The audio sample rate.
        numChannels : List[int]
            Total number of channels.
        interval : float
            The time interval in which the callback should be called.

        """
        # super().__init__(None)
        self.running = running
        self.q = q
        self.FPS = FPS
        self.interval = 1/FPS
        self.numSamples = (winsize if type(winsize) == int
                           else int(winsize * samplerate + 0.5))
        if type(numChannels) == int:
            numChannels = [numChannels]
        self.numChannels = list(numChannels)
        self.samplerate = samplerate
        self.data = []
        for io in range(len(numChannels)):
            self.data.append(zeros((self.numSamples, self.numChannels[io])))
        return

    def register_queue(self, q: Queue):
        """
        Register the `Streamer` queue.

        This function is called by the `Streamer` object during a call to
        `register_monitor` and is not intened to be called on its own.

        Parameters
        ----------
        q : Queue
            The `Streamer` queue.

        """
        self.q = q
        return

    def setup(self):
        """
        Start any necessary object for the monitoring process.

        If a `Monitor` subclass need to initialize some objects before
        receiving data from `Streamer`, like initializing figures or widgets,
        this method must be overriden for this purpose.

        """
        pass

    def process_data(self, data: List[ndarray]):
        """
        Process the data and update monitor display.

        This method receives the amount of data specified by
        `winsize` so it can process the data and display any output.

        This method must be overriden in sublcasses.

        Parameters
        ----------
        data : ndarray
            The audio data from `Streamer` queue.

        """
        pass

    def tear_down(self):
        """
        Destroyer method.

        This method can be implemented to destroy any object that was
        initialized on `setup`, if needed.

        """
        pass


class MonitorProcess(Process, Monitor):
    """Monitor process implementation."""

    def __init__(self, *args, **kwargs):
        Process.__init__(self, name='MonitorProcess')
        Monitor.__init__(self, *args, **kwargs)
        return

    def run(self):
        """
        Overriden process `run` method.

        `setup` the monitor and wait for stream `running` flag to be set.
        Loop over the queue to retrieve data from audio stream and call
        `process_data` to feed the up to date data for visualization.
        After stream stops, run untill queue is empty and call `tear_down` to
        release memory allocated on setup.

        Returns
        -------
        None.

        """
        self.setup()
        self.running.wait()
        last = time()
        while True:
            elapsed = time() - last
            if elapsed < self.interval:
                sleep(self.interval - elapsed)
            frameCount = 0
            while True:
                try:
                    data = self.q.get(timeout=self.interval)
                except Empty:
                    break
                for io in range(len(self.numChannels)):
                    shift = len(data[io])
                    self.data[io] = roll(self.data[io], -shift, axis=0)
                    self.data[io][-shift:, :] = data[io]
                frameCount += shift
                if frameCount >= self.numSamples:
                    break
            self.process_data(self.data)
            if frameCount == 0 and not self.running.is_set():
                break
        self.tear_down()
        return


class MonitorThread(Thread, Monitor):
    """Monitor thread implementation."""

    def __init__(self, *args, **kwargs):
        Thread.__init__(self, name='MonitorThread')
        Monitor.__init__(self, *args, **kwargs)
        return

    def run(self):
        """
        Overriden process `run` method.

        `setup` the monitor and wait for stream `running` flag to be set.
        Loop over the queue to retrieve data from audio stream and call
        `process_data` to feed the up to date data for visualization.
        After stream stops, run untill queue is empty and call `tear_down` to
        release memory allocated on setup.

        Returns
        -------
        None.

        """
        self.setup()
        self.running.wait()
        last = time()
        while True:
            elapsed = time() - last
            if elapsed < self.interval:
                sleep(self.interval - elapsed)
            frameCount = 0
            while True:
                try:
                    data = self.q.get(timeout=self.interval)
                except Empty:
                    break
                for io in range(len(self.numChannels)):
                    shift = len(data[io])
                    self.data[io] = roll(self.data[io], -shift, axis=0)
                    self.data[io][-shift:, :] = data[io]
                frameCount += shift
                if frameCount >= self.numSamples:
                    break
            self.process_data(self.data)
            if frameCount == 0 and not self.running.is_set():
                break
        self.tear_down()
        return
