#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Playback example using system default host and device."""

import realtimesound as rts
from numpy import random
from plotmonitor import WavePlotMonitor


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.hosts('default').default_device()
    device.outputs = [0]
    device.inputs = [1]

    device.plug_monitor(WavePlotMonitor, kwargs={'downsampling': 5})
    audio = random.randn(8*device.samplerate, 1)  # 8 seconds random noise
    audio /= abs(audio).max()  # normalized between [-1, 1]

    device.play(audio)
