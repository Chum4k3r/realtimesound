# -*- coding: utf-8 -*-
"""System host for audio devices."""

from sounddevice import query_hostapis, query_devices,\
    DeviceList, _InputOutputPair as IOPair, default
from realtimesound.device import Device
from typing import List, Dict, Any

from realtimesound.exceptions import InvalidHostName


_default_host_id = default.hostapi


class Host:
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
    def default_devices_ids(self) -> List[int]:
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
        device = Device(iop, data, self, samplerate)
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
        return self.devices(*self.default_devices_ids, samplerate)


class _HostsList(tuple):
    """Listing interface for host APIs."""

    __slots__ = ()

    def __str__(self) -> str:
        """Human readable representation of the contents."""
        text = '\n'.join((f"\n  {idh}) {host.name}:\n" + ''.join(f"{host.devices()}") for idh, host in enumerate(self)))
        return text

    def get(self, idx: int or str):
        return host(idx)


def __enlist_hosts(hosts_data: tuple[dict[str: Any]]):
    return _HostsList([Host(idx, data) for idx, data in enumerate(hosts_data)])


__all_hosts = __enlist_hosts(query_hostapis())


def all_hosts() -> _HostsList:
    """
    All system available hosts in a `HostsList`.

    The `HostsList` generated can be `str`ed for a useful visualization of the info about the host and its available devices.
    It also can `get()` a `Host` object by its index (`idx`) or its `name`. See `get_host` for more information.

    HostsList
        List of all available hosts on system.

    """
    return __all_hosts


def host(*, idx: int = None, name: str = None) -> Host:
    """
    Return a `Host` instance that can create `Device` objects.

    Only one of the arguments must be passed. If both are passed, only `idx` will be looked at, if both are `None`, raises an error.

    Parameters
    ----------
    idx : int
        Host id
    name : str
        Host name

    Raises
    ------
    TypeError
        No arguments provided.
    InvalidHostNames
        Requested name is not a host name.

    Returns
    -------
    Host
        System host for audio devices.
    """
    if idx is not None:
        return __all_hosts[idx]
    elif name is not None:
        return _get_host_by_name(name)
    else:
        raise TypeError("No arguments provided")


def default_host():
    """System host."""
    return host(_default_host_id)


def _is_host_name(host: Host, name: str) -> bool:
    return name.upper() in host.name.upper()


def _get_host_by_name(name):
    hosts_with_name = [host for host in all_hosts() if _is_host_name(host, name)]
    assert len(hosts_with_name) == 1, f"There are {len(hosts_with_name)} hosts with name {name}"
    return hosts_with_name[0]
