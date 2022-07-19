"""
Quando uma chamada de play é feita ao contexto, um gerador do audio a ser tocado é criado e passado ao thread source

Quando uma chamada de record é feita ao contexto, um receptor de áudio a ser gravado é criado e passado ao thread sink

Numa chamada playrec, um gerador e um receptor são criados e passados aos threads source e sink.
"""

from numpy import float32, log10, ndarray, zeros
from numpy.core.shape_base import hstack, vstack
from typing import Generator


def root_mean_square(data: float or ndarray) -> float:
    if isinstance(data, ndarray):
        return (data**2).mean()**0.5
    elif isinstance(data, float):
        return 10**(data / 20)


def decibel(rms: float = None, *, ref: float = 1., power: bool = False, data: ndarray = None) -> float:
    if data is not None:
        return decibel(rms=root_mean_square(data), ref=ref, power=power)
    power_factor = 10 if power else 20
    ref_modifier = 1/ref
    return power_factor * log10(rms * ref_modifier)




def set_audio_level(level: float, audio: ndarray) -> None:
    audio *= (2**0.5 * root_mean_square(level) / root_mean_square(audio))
    return audio



class AudioData(ndarray):
    """From [numpy documentation](https://docs.scipy.org/doc/numpy-1.13.0/user/basics.subclassing.html#simple-example-adding-an-extra-attribute-to-ndarray)."""
    def __new__(subtype, shape, dtype=float32, buffer=None, offset=0,
                strides=None, order=None, samplerate=None):
        obj = super(AudioData, subtype).__new__(subtype, shape, dtype,
                                                buffer, offset, strides,
                                                order)
        obj.samplerate = samplerate
        return obj

    def __array_finalize__(self, obj):
        if obj is None: return
        self.samplerate = getattr(obj, 'samplerate', None)
        return

    @property
    def channels(self) -> int:
        """Número de canais."""
        return self.shape[1]

    @property
    def frames(self) -> int:
        """Número de amostras em cada canal."""
        return self.shape[0]

    @property
    def samples(self) -> int:
        """Número de amostras total."""
        return self.size

    @property
    def duration(self) -> float:
        return self.frames / self.samplerate

    @property
    def RMS(self) -> float:
        return root_mean_square(self)

    @property
    def level(self) -> float:
        return 20 * log10(self.RMS)

    def set_level(self, level: float) -> None:
        set_audio_level(level, self)
        return


class AudioGenerator(object):
    """Basic audio data generator."""

    @staticmethod
    def prepare_for_playing(audio: ndarray, size: int, channels: int) -> Generator:
        data = audio.copy()
        if len(data.shape) == 1:
            data.resize(data.size, 1)
        if len(data.shape) == 2:
            if data.shape[1] == 1 and channels > 1:
                data = hstack(channels*[data])
            elif channels == 1 and data.shape[1] > 1:
                data = data.sum(axis=1) / data.shape[1]
            elif channels > 1 and data.shape[1] > 1 and channels != data.shape[1]:
                raise ValueError("Audio has unexpected number of channels.")
        data.resize(round(data.shape[0]/size + 0.5), size, channels)
        return (chunk for chunk in data)

    def __init__(self, audio: ndarray, numoutputs: int, blocksize: int = 128):
        self.channels = numoutputs
        self.size = blocksize
        self.audiogen = self.prepare_for_playing(audio, self.size, self.channels)
        return

    def emplace_audio(self, audio: ndarray):
        self.audiogen = self.prepare_for_playing(audio, self.size, self.channels)
        return

    def next_audio_block(self) -> ndarray:
        return next(self.audiogen)


class AudioReceiver(object):
    """Basic audio data receiver."""

    def __init__(self, numinputs: int, numsamples: int):
        self.channels = numinputs
        self.size = numsamples
        self.audiorec = zeros((0, self.channels), float32)
        return

    def emplace_size(self, numsamples: int):
        self.size = numsamples
        self.audiorec = zeros((0, self.channels), float32)
        return

    def next_audio_block(self, block: ndarray):
        self.audiorec = vstack((self.audiorec, block))
        if self.audiorec.shape[0] > self.size:
            self.audiorec = self.audiorec[:self.size]
            raise StopIteration
        return
