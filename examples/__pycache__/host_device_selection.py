from typing import Any
from sounddevice import OutputStream, query_devices, query_hostapis
from pprint import pprint
from dataclasses import dataclass, field
from typing import Mapping


class HostNameNotFoundError(Exception):
    def __init__(self, hosts: tuple[dict[str, Any]], name: str) -> None:
        self.host_names = [api['name'] for api in hosts]
        self.requested_name = name
        return

    def __str__(self):
        return f"Name {self.requested_name} not found.\nAvailable names are:\n{self.host_names}"


@dataclass
class IOPair:
    input: Any
    output: Any

    def __post_init__(self):
        assert type(self.input) == type(self.output), f"Pair must have same type.\nType I: {type(self.input).__name__}, Type O: {type(self.output).__name__}"

@dataclass
class Device:
    idx: int
    name: str
    samplerate: int
    host_id: int
    max_channels: int
    hi_latency: float
    lo_latency: float


@dataclass
class AudioHost:
    idx: int
    name: str
    default_device: IOPair
    devices: list

    def default_devices(self) -> IOPair[Device]:
        return default_host_devices(self)


def get_host_by_name(name: str) -> AudioHost:
    hostlist = query_hostapis()
    for idx, api in enumerate(hostlist):
        if api['name'] == name:
            default = IOPair(input=api['default_input_device'], output=api['default_output_device'])
            return AudioHost(idx=idx, name=name, default_device=default, devices=api['devices'])
    else:
        raise HostNameNotFoundError(hostlist, name=name)
    

def _build_device(device_data: dict[str, Any], idx: int, host: AudioHost, IO: str) -> Device:
    return Device(
        idx=idx,
        name=device_data['name'],
        samplerate=device_data['default_samplerate'],
        host=host.idx,
        max_channels=device_data[f'max_{IO}_channels'],
        hi_latency=device_data[f'default_high_{IO}_latency'],
        lo_latency=device_data[f'default_low_{IO}_latency']
    )


def get_input_device(idx: int, host: AudioHost) -> Device:
    device_data = query_devices(idx)
    return _build_device(device_data, idx, host, 'input')
    

def get_output_device(idx: int, host: AudioHost) -> Device:
    device_data = query_devices(idx)
    return _build_device(device_data, idx, host, 'output')


def default_host_devices(host: AudioHost):
    idevice = get_input_device(host.default_device.input, host)
    odevice = get_output_device(host.default_device.output, host)
    return IOPair(input=idevice, output=odevice)


def main():
    WASAPI_NAME = "Windows WASAPI"

    wasapi = get_host_by_name(WASAPI_NAME)
    print(wasapi)

    devices = default_host_devices(wasapi)
    print(devices)


if __name__ == '__main__':
    main()