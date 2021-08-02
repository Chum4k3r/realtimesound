#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use system default host and device.

In this example a `Device` instance is created by requesting the default
input/output (I/O) pair of devices from the default system host API.

A `Monitor` is plugged to the device.
A 10 seconds audio is recorded using the device.
The `.record` method receives the `block=False` argument, that ensures the
imediate return, allowing the code to enter a loop that keeps printing to the
screen the RMS of the whole recording buffer, which starts filled with zeros,
and gets constantly updated.

The recorded data is then played.

"""

import realtimesound as rts
from plotmonitor import WavePlotMonitor, BarPlotMonitor
from time import time


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.hosts('asio').default_device()

    device.plug_monitor(WavePlotMonitor, kwargs={'downsampling': 10,
                                                 'FPS': 48,
                                                 'winsize': 0.2})

    rec = device.record(10., block=False)

    start = time()
    while (time() - start) < 10.:
        print(f"\rRMS(rec): {(rec**2).mean(axis=0)**0.5}\r", end='\r')

    device.play(rec, block=False)
