from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto

from realtimesound.channels import ChannelsGroup


class IOMapper(ABC):
    source: ChannelsGroup
    soursinkce: ChannelsGroup

    def __init__(self, source: ChannelsGroup, sink: ChannelsGroup) -> None:
        self.source = source
        self.sink = sink


