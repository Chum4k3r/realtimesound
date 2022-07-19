# -*- coding: utf-8 -*-
"""Audio input and output device."""

from sounddevice import _InputOutputPair as IOPair,\
    check_input_settings, check_output_settings
from typing import Any, Dict, List

from realtimesound.channels import Channel, ChannelsGroup




def _make_iopair(input_data: Any, output_data: Any) -> IOPair:
    pair = IOPair(None, None)
    pair['input'] = input_data
    pair['output'] = output_data
    return pair


def _device_samplerate(data: IOPair) -> IOPair:
    return _make_iopair(data['input']['samplerate'], data['output']['samplerate'])


def _device_name(data: IOPair) -> IOPair:
    return _make_iopair(data['input']['name'], data['output']['name'])


def _device_max_channels(data: IOPair) -> IOPair:
    return _make_iopair(data['input']['max_input_channels'], data['output']['max_output_channels'])


def _device_default_low_latency(data: IOPair) -> IOPair:
    return _make_iopair(data['input']['default_low_input_latency'], data['output']['default_low_output_latency'])


def _device_default_high_latency(data:IOPair) -> IOPair:
    return _make_iopair(data['input']['default_high_input_latency'], data['output']['default_high_output_latency'])


def _device_channels_list(channels: int or List[int], samplerate: int) -> List[Channel]:
    if isinstance(channels, int):
        channels = range(channels)
    return [Channel(num=ch, samplerate=samplerate) for ch in channels]


def is_valid_channels(chlist: List[int]) -> bool:
    if chlist:
        if len(chlist) > 0:
            return True
    return False


class Device:
    def __init__(self, id: IOPair, device_data: IOPair, host: object, samplerate: int = None,
                 inputs: ChannelsGroup = None, outputs: ChannelsGroup = None):
        if not samplerate:
            samplerate = _device_samplerate(device_data)
        max_channels = _device_max_channels(device_data)
        if not is_valid_channels(inputs):
            inputs = _device_channels_list(max_channels['input'], samplerate)
        if not is_valid_channels(outputs):
            outputs = _device_channels_list(max_channels['output'], samplerate)
        check_input_settings(id['input'], max(inputs).num + 1, 'float32', None, samplerate)
        check_output_settings(id['output'], max(outputs).num + 1, 'float32', None, samplerate)
        self._id = id
        self._data = device_data
        self._host = host
        self._channels = _make_iopair(inputs.sort(), outputs.sort())
        self._samplerate = samplerate

        return

    @property
    def id(self) -> IOPair:
        return self._id

    @property
    def name(self) -> IOPair:
        return _device_name(self._data)

    @property
    def samplerate(self) -> IOPair:
        return self._samplerate

    @property
    def max_channels(self):
        return _device_max_channels(self._data)

    @property
    def channels(self):
        return self._channels

    @property
    def host(self):
        return self._host

    @property
    def default_low_latency(self):
        return _device_default_low_latency(self._data)

    @property
    def default_high_latency(self):
        return _device_default_high_latency(self._data)



class SystemDevice(object):
    """Audio device object abstraction."""

    def __init__(self,
                 id: IOPair,
                 device_data: IOPair,
                 host: object,
                 samplerate: int = None,
                 inputs: List[int] = None,
                 outputs: List[int] = None):
        """
        Provide functionality to playback and record audio data.

        Parameters
        ----------
        hostapi : object
            The Host object.
        id : IOPair
            Input and output device id on Host.
        device_data : IOPair
            Input and output device description as dicts.
        samplerate : int, optional
            Amount of samples per second. The default is None.
        inputs : List[int], optional
            List of active input channels. If None, activate all.
            The default is None.
        outputs : List[int], optional
            List of active output channels. If None, activate all.
            The default is None.

        Returns
        -------
        None.

        """
        if samplerate is None:
            samplerate = max(device_data['input']['default_samplerate'],
                             device_data['output']['default_samplerate'])
        if inputs is None:
            inputs = list(range(device_data['input']['max_input_channels']))
        inputs.sort()
        if outputs is None:
            outputs = list(range(device_data['output']['max_output_channels']))
        outputs.sort()
        check_input_settings(id['input'], inputs[-1] + 1, 'float32', None, samplerate)
        check_output_settings(id['output'], outputs[-1] + 1, 'float32', None, samplerate)

        super().__init__()
        self._id = id
        self._host = host
        self._samplerate = samplerate
        self._inputs = inputs
        self._outputs = outputs

        channels = IOPair(None, None)
        channels['input'] = len(inputs)
        channels['output'] = len(outputs)
        self._channels = channels

        name = IOPair(None, None)
        name['input'] = device_data['input']['name']
        name['output'] = device_data['output']['name']
        self._name = name

        maxchannels = IOPair(None, None)
        maxchannels['input'] = device_data['input']['max_input_channels']
        maxchannels['output'] = device_data['output']['max_output_channels']
        self._maxchannels = maxchannels

        defaultLowLatency = IOPair(None, None)
        defaultLowLatency['input'] = device_data['input']['default_low_input_latency']
        defaultLowLatency['output'] = device_data['output']['default_low_Output_latency']
        self._defaultLowLatency = defaultLowLatency

        defaultHighLatency = IOPair(None, None)
        defaultHighLatency['input'] = device_data['input']['default_high_input_latency']
        defaultHighLatency['output'] = device_data['output']['default_high_output_latency']
        self._defaultHighLatency = defaultHighLatency

        self._data = device_data
        return

    @property
    def id(self) -> IOPair:
        """Device input and output unique IDs on system."""
        return self._id

    @property
    def samplerate(self) -> int:
        """Amount of samples per second."""
        return self._samplerate

    @samplerate.setter
    def samplerate(self, fs):
        if not self._online.is_set():
            check_input_settings(self.id['input'], self.inputs[-1] + 1,
                                 'float32', None, fs)
            check_output_settings(self.id['output'], self.outputs[-1] + 1,
                                  'float32', None, fs)
            self._samplerate = int(fs)
        return

    @property
    def inputs(self) -> List[int]:
        """Active input channels."""
        return self._inputs

    @inputs.setter
    def inputs(self, mapping: List[int]):
        if (len(mapping) > self.maxInputs
                or max(mapping) >= self.maxInputs):
            raise ValueError("Too many channels or unavailable channel number.")
        mapping.sort()
        check_input_settings(self.id['input'], mapping[-1] + 1,
                                'float32', None, self.samplerate)
        self._inputs.clear()
        self._inputs.extend(mapping)
        self._inputs.sort()
        self._channels['input'] = len(self._inputs)
        return

    @property
    def outputs(self) -> List[int]:
        """Active output channels."""
        return self._outputs

    @outputs.setter
    def outputs(self, mapping: List[int]):
        if (len(mapping) > self.maxOutputs
                or max(mapping) >= self.maxOutputs):
            raise ValueError("Too many channels or unavailable channel number.")
        mapping.sort()
        check_output_settings(self.id['output'], mapping[-1] + 1,
                                'float32', None, self.samplerate)
        self._outputs.clear()
        self._outputs.extend(mapping)
        self._outputs.sort()
        self._channels['output'] = len(self._outputs)
        return

    @property
    def channels(self) -> List[int]:
        """Total active [input, output] channels."""
        return [len(self.inputs), len(self.outputs)]

    @property
    def name(self):
        return self._name

    @property
    def host(self):
        """Device's host object."""
        return self._host

    @property
    def maxChannels(self):
        return self._maxchannels

    @property
    def defaultLowLatency(self):
        """Low latency value for [input, output]."""
        return self._defaultLowLatency

    @property
    def defaultHighLatency(self):
        """High latency value for [input, output]."""
        return self._defaultHighLatency
