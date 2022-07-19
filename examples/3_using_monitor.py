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

Between the playbacks and the recordings, some `Monitor`s are plugged to the
`Device` with some keyworded arguments to manipulate the `Monitor` parameters.

The `Monitor` is an independent `multiprocessing.Process`, thus can only be
started once, and then must be `.join`ed and `.close`ed to free resources.
This is why the classes are passed in as arguments to the `.plug_monitor` method.

Once a `Monitor` is plugged to the `Device`, it will be always invoked whenever
the `Device` calls `.play`, `.record` or `.playrec`.

"""

import realtimesound as rts
from numpy import random
from plotmonitor import WavePlotMonitor, BarPlotMonitor


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    device = rts.default_host().default_device()

    ctx = rts.create_context(device)

    ctx.plug_monitor(WavePlotMonitor, kwargs={'downsampling': 10,
                                                 'FPS': 48,
                                                 'winsize': 0.2})

    rec = ctx.record(6.)

    ctx.plug_monitor(BarPlotMonitor, kwargs={'FPS': 60,
                                                'winsize': 1/8})

    ctx.play(rec)

    audio = random.randn(8*device.samplerate, 1)  # 8 seconds random noise
    audio /= abs(audio).max()  # normalized between [-1, 1]

    recaudio = ctx.playrec(audio)

    ctx.plug_monitor(WavePlotMonitor, kwargs={'downsampling': 10})
    ctx.play(recaudio)
