from enum import Enum, auto
from dataclasses import dataclass, field
from numpy import array, ndarray, zeros
from numpy.core import machar

from realtimesound.audio import AudioData


class StereoLevel:
    def __init__(self, left: int, right: int) -> None:
        self.left=left
        self.right=right
        return
    
    def set_weight(self, data: ndarray) -> ndarray:
        return data * self.levels()

    def levels(self):
        return [self.left, self.right]



class ChannelRole(Enum):
    BASS = auto()
    FRONT = auto()
    FRONT_LEFT = auto()
    LEFT = auto()
    BACK_LEFT = auto()
    BACK = auto()
    BACK_RIGHT = auto()
    RIGHT = auto()
    FRONT_RIGHT = auto()


class CConfiguration(Enum):
    MONO = '1'
    MONO_BASS = '1.1'
    STEREO = '2'
    STEREO_BASS = '2.1'
    FOUR = '4'
    FOUR_BASS = '4.1'
    FIVE_BASS = '5.1'
    SIX = '6'
    SEVEN_BASS = '7.1'


@dataclass(order=True)
class Channel:
    num: int
    role: ChannelRole
    samplerate: int = field(compare=False)
    mute: bool = field(default=False, compare=False)
    solo: bool = field(default=False, compare=False)
    phase_shift: bool = field(default=False, compare=False)
    data: ndarray = None

    @property
    def num_frames(self) -> int:
        return self.data.shape[0]

    @property
    def audio_duration(self) -> float:
        return self.num_frames/self.samplerate


@dataclass
class ChannelsGroup:
    _group: list[Channel]
    setting: CConfiguration
    audio: AudioData


    def active_channels(self) -> list[Channel]:
        not_muted = [channel for channel in self._group if not channel.mute]
        soloed = [ch for ch in not_muted if ch.solo]
        if len(soloed):
            return soloed
        return not_muted

