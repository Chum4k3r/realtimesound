# -*- coding: utf-8 -*-
"""System host for audio devices."""

from sounddevice import query_hostapis, query_devices,\
    DeviceList, _InputOutputPair as IOPair, default
from realtimesound.device import Device
from typing import List, Dict, Any


_default_host_id = default.hostapi


class Host(object):
    """Host API object abstraction."""

    def __init__(self, id: int, data: Dict[str, Any]):
        """
        Host audio system for device listing and stream creation.

        This class should not be directly created, instead, provide the desired
        host index from the `hosts` function output.

        Parameters
        ----------
        id : int
            System unique identification of the host.
        data : Dict[str, Any]
            Host information taken from the system.

        Returns
        -------
        None.

        """
        self.id = id
        self._data = data
        return

    def __repr__(self) -> str:
        """Representation of the host."""
        return self.name

    @property
    def name(self) -> str:
        """Audio host name on system."""
        return self._data['name']

    @property
    def defaultDevicesID(self) -> List[int]:
        """Indexes of the default [input, output] devices for this host."""
        return [self._data['devices'].index(self._data['default_input_device']),
                self._data['devices'].index(self._data['default_output_device'])]

    def devices(self,
                in_id: int = None,
                out_id: int = None,
                samplerate: int = None) -> Device or DeviceList:
        """
        Query the available devices for this host.

        If `in_id` or `out_id` are not supplied, returns a `DeviceList` object
        that holds information about each of the host devices and is suited
        for using with `print` function for visualization.

        If both `in_id` and `out_id` are given and exists within this host
        devices list, returns a `Device` object, which can be used to play and
        record audio as `numpy.ndarray` objects.

        Parameters
        ----------
        in_id : int, optional
            ID of the desired input device. The default is None.
        out_id : int, optional
            ID of the desired output device. The default is None.
        samplerate : int, optional
            A sample rate to use with both devices. If not given, uses the
            greater default sample rate of the devices.
            The default is None.

        Raises
        ------
        ValueError
            Either `in_id` or `out_id` not in `self.devices()`.

        Returns
        -------
        Device
            Object that refers to an input and output device pair for running
            PortAudio streams on parallel process.
        DeviceList:
            Custom display of the host available devices.

        """
        if in_id is None or out_id is None:
            return DeviceList(query_devices(d) for d in self._data['devices'])
        iop = IOPair(None, None)
        iop['input'] = self._data['devices'][in_id]
        iop['output'] = self._data['devices'][out_id]
        if (iop['input'] not in self._data['devices']
                or iop['output'] not in self._data['devices']):
            raise ValueError("Device not available for this HostAPI.")
        data = IOPair(None, None)
        data['input'] = query_devices(iop['input'])
        data['output'] = query_devices(iop['output'])
        if samplerate is None:
            samplerate = int(max(data['input']['default_samplerate'],
                                 data['output']['default_samplerate']))
        device = Device(self, iop, data, samplerate)
        return device

    def default_device(self, samplerate: int = None) -> Device:
        """
        Create a `Device` object using `defaultDevicesID`.

        Parameters
        ----------
        samplerate : int, optional
            A sample rate to use with both devices. If not given, uses the
            greater default sample rate of the devices.
            The default is None.

        Returns
        -------
        Device
            Object that refers to an input and output device pair for running
            PortAudio streams on parallel process.

        See Also
        --------
        `devices`

        """
        return self.devices(*self.defaultDevicesID, samplerate)


class HostsList(tuple):
    """Listing interface for host APIs."""

    __slots__ = ()

    def __repr__(self) -> str:
        """Human readable representation of the contents."""
        text = '\n'.join(f"\n  {idh}) {host['name']}:\n"
                         + '\n'.join(f"    {idd} {device['name']}: "
                                     + f"({device['max_input_channels']} in, "
                                       + f"{device['max_output_channels']} out)"
                                     for idd, device in enumerate(query_devices(dev)
                                                                  for dev in host['devices']))
                         for idh, host in enumerate(self))
        return text


def hosts(idx: int or str = None) -> Host or HostsList:
    """
    All system available hosts in a `HostsList` or return a `Host` instance.

    If no `idx` is provided, a `HostsList` will be generated and can be
    `print`ed for a useful visualization of the info about the host and its
    available devices.

    If `idx` is not None, return a `Host` instance that can create `Device`
    objects that can play and record audio data.
    The given `idx` might be an integer representing the host ID or a string
    representing the host Name.

    Parameters
    ----------
    idx : int or str, optional
        Host id or name. The default is None.

    Raises
    ------
    ValueError
        If the provided name is not available or mispelled.

    Returns
    -------
    Host
        System host for audio devices.
    HostsList
        List of all available hosts on system.

    """
    if idx is not None:
        if type(idx) == str:
            if idx.lower() == 'default':
                idx = _default_host_id
            else:
                try:
                    idx = [i for i, host in enumerate(hosts())
                           if idx.upper() in host['name'].upper().split(' ')][0]
                except IndexError:
                    raise ValueError("Invalid API name.")
        return Host(idx, query_hostapis(idx))
    return HostsList(query_hostapis())
