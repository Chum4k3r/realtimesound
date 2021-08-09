#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use system default host and device.

In this example a `Device` instance is created by requesting the default
input/output (I/O) pair of devices from the default system host API.

A 6 seconds audio is recorded using the device.
The recorded audio is played back again.
Then a numpy array of random data worth of 8 seconds of audio is created and
used for simultaneous playback and recording.
The recorded data is then played.

"""

import realtimesound as rts
from numpy import random


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.hosts('asio').default_device()

    rec = device.record(3.)

    device.play(rec)

    audio = random.randn(8*device.samplerate, 1)  # 8 seconds random noise
    audio /= abs(audio).max()  # normalized between [-1, 1]

    recaudio = device.playrec(audio)

    device.play(recaudio)
