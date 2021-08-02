#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
List and select system audio host and I/O device.

The code print the list of available hosts and its respective devices, then
query for the ID of the host. The ID can be both the unique number or the
name, e.g. id='asio' for ASIO host, or 'wasapi' for Windows WASAPI.
The information about the selected host is printed.

The available devices for the chosen host is printed and the code query for
the input, output pair of device indexes. The unique numbers must be used here,
as the names can be repeated from host to host.

"""

import realtimesound as rts


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    print(rts.hosts())
    hid = int(input("Enter the desired host number id: "))

    host = rts.hosts(hid)
    print(f'{host.id} {host.name} (default devices: {host.defaultDevicesID})\n\n')

    print(host.devices())
    did = [int(idx.strip()) for idx
           in input("Enter the devices I/O ids (comma separated): ").split(',')]

    device = host.devices(*did)

    print(f"I: {device.id['input']} {device.inputName} (max inputs: {device.maxInputs})")
    print(f"O: {device.id['output']} {device.outputName} (max outputs: {device.maxOutputs})")
    print(f"Sampling rate: {device.samplerate}")
