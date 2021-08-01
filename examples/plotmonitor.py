# -*- coding: utf-8 -*-
"""
Pyplot based monitor.

This file shows an example construction of a `Monitor` subclass that can be
used as base class for any `matplotlib` graphical display of the audio data.

Two implementations are also provided, `BarPlotMonitor` and `WavePlotMonitor`,
both can be used to visualize data and to provide reference on coding your
own monitors.

"""

from realtimesound.monitor import Monitor
from typing import List
from numpy import ndarray, seterr, random, log10, arange
from matplotlib import use
use("qt5agg")
from matplotlib import pyplot as plt


class PlotMonitor(Monitor):
    """Class for monitoring audio streams using `matplotlib` graphics."""

    def __init__(self, FPS: int = 30, winsize: int or float = 1/8, *args, **kwargs):
        """
        Show the input signal during record.

        Parameters
        ----------
        samplerate : int
            The audio sample rate.
        numChannels : List[int]
            Total number of channels.
        interval : float
            The time interval in which the callback should be called.

        """
        super().__init__(FPS, winsize, *args, **kwargs)
        return

    def setup(self):
        """
        Build a single figure and an axis for each stream direction.

        After the figure and axis creation, the `plot_setup` method is called
        to draw lines, bars, or whichever figure is desired to be shown in the
        plot.

        Returns
        -------
        None.

        """
        self.fig, self.ax = plt.subplots(len(self.numChannels), 1)
        self.plot_setup()
        self.fig.canvas.draw()
        plt.show(block=False)
        return

    def plot_setup(self):
        """
        Abstract method, must be overriden.

        Any drawing that will be updated on the figure should be created here.
        This includes lines, bars, and other objects.

        Returns
        -------
        None.

        """
        pass

    def process_data(self, data: List[ndarray]):
        """
        Process and update the plot inside the monitor loop.

        Will be called at `interval` time spaces to update the monitor buffer
        and the graphical view, ensuring the FPS requested is matched.

        Parameters
        ----------
        data : List[ndarray]
            Contains the stream callback `indata` and/or `outdata`.

        Returns
        -------
        None.

        """
        seterr(divide='ignore')
        self.update_plot_data(data)
        self.fig.canvas.update()
        self.fig.canvas.flush_events()
        return

    def update_plot_data(self, data: List[ndarray]):
        """
        Abstract method. Must be overriden to provide proper update of the draws.

        This method is called inside `process_data` to update the contents of
        the lines, bars and other object created inside `plot_setup`.

        Parameters
        ----------
        data : List[ndarray]
            Contains the stream callback `indata` and/or `outdata`.

        Returns
        -------
        None.

        """
        pass

    def tear_down(self):
        """Close the figure and release graphical resources."""
        plt.close()
        return


class BarPlotMonitor(PlotMonitor):
    """Class for monitoring audio with bar plots."""

    def __init__(self, *args, **kwargs):
        """
        Show the audio level during playback and/or record.

        Parameters
        ----------
        samplerate : int
            The audio sample rate.
        numChannels : List[int]
            Total number of channels.
        interval : float
            The time interval in which the callback should be called.

        See Also
        --------
        `Monitor`

        """
        super().__init__(*args, **kwargs)
        return

    def plot_setup(self):
        """
        Construct the bar plot.

        Elaborate channel information as a list of strings, then checks if the
        stream is single sided (input OR output) or duplex (input AND output).
        Creates a bar for each channel on each side of the stream with a dummy
        value, sets the limits and return.

        Returns
        -------
        None.

        """
        channels = [[f'ch. {n}' for n in range(nch)] for nch in self.numChannels]
        seterr(divide='ignore')
        if len(self.numChannels) > 1:
            self.bars = []
            for io, nch in enumerate(self.numChannels):
                dummy = random.randn(int(round(self.numSamples + 0.5)), nch)
                self.bars.append(self.ax[io].bar(
                    channels[io], 20*log10((dummy**2).mean(axis=0)**0.5), bottom=-150))
                self.ax[io].set_ylim([-100, 1])
        elif len(self.numChannels) == 1:
            dummy = random.randn(int(round(self.numSamples + 0.5)),
                                 self.numChannels[0])
            self.bars = self.ax.bar(
                channels[0], 20*log10((dummy**2).mean(axis=0)**0.5), bottom=-150)
            self.ax.set_ylim([-100, 1])
        return

    def update_plot_data(self, data: List[ndarray]):
        """
        Set the bar heights for next draw.

        Check if the stream is single sided or duplex, update each bar height
        with the level of each channel, and returns.

        Parameters
        ----------
        data : List[ndarray]
            Contains the stream callback `indata` and/or `outdata`.

        Returns
        -------
        None.

        """
        if len(self.numChannels) > 1:
            for io, (nch, audio) in enumerate(zip(self.numChannels, data)):
                self.ax[io].draw_artist(self.ax[io].patch)
                for ch in range(nch):
                    h = 20*log10((audio[:, ch]**2).mean()**0.5)
                    self.bars[io][ch].set_height(h + 150)
                    self.ax[io].draw_artist(self.bars[io][ch])
        elif len(self.numChannels) == 1:
            self.ax.draw_artist(self.ax.patch)
            for ch in range(self.numChannels[0]):
                h = 20*log10((data[0][:, ch]**2).mean()**0.5)
                self.bars[ch].set_height(h + 150)
                self.ax.draw_artist(self.bars[ch])
        return


class WavePlotMonitor(PlotMonitor):
    """Class for visualize downsampled audio waveform in real time."""

    def __init__(self, downsampling: int = 10, *args, **kwargs):
        """
        Show the downsampled audio waveform during playback and/or record.

        Parameters
        ----------
        downsampling : int
            Interval of which samples will be shown. The default is 10.

        Returns
        -------
        None.

        See Also
        --------
        `Monitor`

        """
        super().__init__(*args, **kwargs)
        self.downsampling = downsampling
        return

    def plot_setup(self):
        """
        Consruct the wave lines.

        Checks if the stream is single sided (input OR output) or duplex
        (input AND output), plot a line for each channel on each side,
        setup the limits and return.

        Returns
        -------
        None.

        """
        time = arange(0, self.numSamples/self.samplerate,
                      self.downsampling/self.samplerate)
        if len(self.numChannels) > 1:
            self.lines = []
            for io, nch in enumerate(self.numChannels):
                dummy = random.randn(int(round(self.numSamples/self.downsampling + 0.5)), nch)
                self.lines.append(self.ax[io].plot(time, dummy))
                self.ax[io].set_ylim([-1.1, 1.1])
        elif len(self.numChannels) == 1:
            dummy = random.randn(int(round(self.numSamples/self.downsampling + 0.5)),
                                 self.numChannels[0])
            self.lines = self.ax.plot(time, dummy)
            self.ax.set_ylim([-1.1, 1.1])
        return

    def update_plot_data(self, data: List[ndarray]):
        """
        Update line contents for next draw.

        Checks if stream is single sided or duplex, update each line with new
        samples from each channel and return.

        Parameters
        ----------
        data : List[ndarray]
            Contains the stream callback `indata` and/or `outdata`.

        Returns
        -------
        None.

        """
        if len(self.numChannels) > 1:
            for io, (nch, audio) in enumerate(zip(self.numChannels, data)):
                self.ax[io].draw_artist(self.ax[io].patch)
                for ch in range(nch):
                    self.lines[io][ch].set_ydata(audio[::self.downsampling, ch])
                    self.ax[io].draw_artist(self.lines[io][ch])
        elif len(self.numChannels) == 1:
            self.ax.draw_artist(self.ax.patch)
            for ch in range(self.numChannels[0]):
                self.lines[ch].set_ydata(data[0][::self.downsampling, ch])
                self.ax.draw_artist(self.lines[ch])
        return
