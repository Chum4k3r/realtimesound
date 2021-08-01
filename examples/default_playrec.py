#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playback and record example using system default host and device."""

import realtimesound as rts
from numpy import random
from plotmonitor import WavePlotMonitor


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.hosts('asio').default_device()
    device.outputs = [0, 1]
    device.inputs = [0, 1]

    device.plug_monitor(WavePlotMonitor, kwargs={'downsampling': 10,
                                                 'winsize': 0.6})
    audio = random.randn(8*device.samplerate, 1)  # 8 seconds random noise
    audio /= abs(audio).max()  # normalized between [-1, 1]

    rec = device.playrec(audio)
