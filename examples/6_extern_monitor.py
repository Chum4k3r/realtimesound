#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Use system default host and device.

In this example a `Device` instance is created by requesting the default
input/output (I/O) pair of devices from the default system host API.

An external monitor is created by requesting the monitor queue and the stream
state flag from the device. This requires that all memory management of the
monitor is made by user.

An audio sample of 8 seconds is created.

Then a call to `turn_on` is made to put the `Device` on continuous streaming mode.
The `Device` can `play`, `record` and `playrec` just like the finite streaming mode.
It can call `turn_off` to finish the streaming.

A `Device` in continuous mode is always nonblocking.

Any change of `Device` properties can only be made if the `Device` is not
continuously streaming.

After `Device.turn_off` call, the monitor is `join`ed and `close`d for proper
memory management.

"""

import realtimesound as rts
from numpy import random
from plotmonitor import WavePlotMonitor
from time import sleep


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.hosts('asio').default_device()

    monitorQ, streamState = device.use_extern_monitor()

    myMonitor = WavePlotMonitor(downsampling=1, FPS=30,
                                winsize=0.1,
                                samplerate=device.samplerate,
                                numChannels=device.channels,
                                running=streamState, q=monitorQ)

    myMonitor.start()

    audio = random.randn(8*device.samplerate, 1)  # 8 seconds random noise
    audio /= abs(audio).max()  # normalized between [-1, 1]

    device.inputs = [0]
    device.outputs = [0]

    device.turn_on()

    sleep(5.)
    rec = device.playrec(audio)
    sleep(10.)

    device.play(rec)
    sleep(10.)

    device.turn_off()

    myMonitor.join(timeout=5.)
    myMonitor.close()
