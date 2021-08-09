#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use system default host and device.

In this example a `Device` instance is created by requesting the default
input/output (I/O) pair of devices from the default system host API.

A monitor is plugged to the device to provide visualization of the data.

An audio sample of 8 seconds is also created.

Then a call to `turn_on` is made to put the `Device` on continuous streaming mode.
The `Device` can `play`, `record` and `playrec` just like the finite streaming mode.
It can call `turn_off` to finish the streaming.

A `Device` in continuous mode is always nonblocking.

Any change of `Device` properties can only be made if the `Device` is not
continuously streaming.

"""

import realtimesound as rts
from numpy import random
from plotmonitor import WavePlotMonitor
from time import sleep


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.hosts('asio').default_device()

    device.plug_monitor(WavePlotMonitor, kwargs={'downsampling': 10,
                                                 'FPS': 48,
                                                 'winsize': 0.2})

    audio = random.randn(1*device.samplerate, 1)  # 8 seconds random noise
    audio /= abs(audio).max()  # normalized between [-1, 1]

    device.inputs = [0]
    device.outputs = [0]

    device.turn_on()

    sleep(1.)
    rec = device.playrec(audio)
    sleep(2.)

    device.play(rec)
    sleep(2.)

    device.turn_off()
