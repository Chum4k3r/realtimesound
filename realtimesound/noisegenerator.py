import numpy as np
from typing import Generator
from enum import Enum

from realtimesound.config import config


class ColorType(Enum):
    PURPLE=-2
    BLUE=-1
    WHITE=0
    PINK=1
    BROWN=2


class InvalidColorType(Exception):
    pass


def noise_generator(nsamples: int = None, nchannels: int = None, samplerate: int = None) -> Generator:
    while True:
        yield colored_noise(color='pink', samplingRate=samplerate, numSamples=nsamples, numChannels=nchannels)


def colored_noise(
        color: ColorType = ColorType.WHITE,
        samplingRate: int = None,
        numSamples: int = None,
        numChannels: int = None,
        # startMargin: float = None,
        # stopMargin: float = None,
        # windowing: str = 'hann'
    ):
    """
    Power law noise generator.
    Based on the algorithm in:
    Timmer, J. and Koenig, M.:
    On generating power law noise.
    Astron. Astrophys. 300, 707-710 (1995)
    Generate random noise with respect to the `(1/f)**B` rate. `f` stands for
    frequency and `B` is an integer power.
    The colors and its spectrum characteristics:
        * Purple | Differentiated:
            * +6.02 dB/octave | +20 dB/decade | B = -2;
            * color: 'purple', 'diff', 'differentiated';
        * Blue | Azure:
            * +3.01 dB/octave | +10 dB/decade | B = -1;
            * color: 'blue', 'azure'
        * White | Flat:
            * +0.00 dB/octave | +0 dB/decade  | B = 0;
            * color: 'white', 'flat';
        * Pink | Flicker:
            * -3.01 dB/octave | -10 dB/decade | B = 1;
            * color: 'pink', 'flicker', '1/f';
        * Red | Brownian:
            * -6.02 dB/octave | -20 dB/decade | B = 2;
            * color: 'red', 'brown', 'brownian';
    The output signal will have `startMargin` silence at the beginning of the
    waveform, and `stopMargin` silence at the end.
    There is a fade-in between the starting silence and the noise itself that
    occurs during 5% of the total noise duration.
    @author: Chum4k3r
    """
    # It was done like this because a function default argument is a value
    # assigned at import time, and PyTTa have a default object that handles
    # default values for all functions and all classes across all submodules.
    # In order to it work as expected, the values should be reassigned at
    # every function call to get updated default values. Otherwise, despite
    # how the default has it's properties values changed, it won't change
    # for the function calls.
    if samplingRate is None:
        samplingRate = config.sampling_rate()
    if numSamples is None:
        numSamples = config.blocksize()
    if numChannels is None:
        numChannels = config.num_channels()[1]
    # if startMargin is None:
    #     startMargin = default.startMargin
    # if stopMargin is None:
    #     stopMargin = default.stopMargin

    startMargin = 0
    stopMargin = 0

    stopSamples = round(stopMargin*samplingRate)

    # [samples] ending silence number of samples
    startSamples = round(startMargin*samplingRate)

    # [samples] total silence number of samples
    marginSamples = startSamples + stopSamples

    # [samples] Actual noise number of samples
    noiseSamples = int(numSamples - marginSamples)

    try:
        if isinstance(color, int):
            color = ColorType(color)
        elif isinstance(color, str):
            color = ColorType[color.upper()]
        noiseSignal = _powerlaw_noise(noiseSamples, numChannels,
                                        color.value, samplingRate)

    except (ValueError, KeyError):
        raise InvalidColorType(f"There is no noise generation for color {color}")


    noiseSignal = np.concatenate(
                (np.zeros((int(startSamples), numChannels)),
                 noiseSignal,
                 np.zeros((int(stopSamples), numChannels)))
            )
    return noiseSignal


def _powerlaw_noise(nsamples, nchannels, power, fs):
    # Choose a power law spectrum
    # w = 2pif
    # S(w) approx (1/w)^B
    freqs = np.fft.rfftfreq(nsamples, 1/fs)
    freqs[0] = 1/nsamples
    scaling = (1/(2 * np.pi * freqs))**(power/2)

    # For each Fourier freq w_i draw 2 gaussian distributed numbers
    # multiply them by sqrt(0.5 * S(w_i)) approx (1/w)^(B/2)
    # the results are the real and imaginary part of
    # the FFT of the data at the frequency
    real = scaling * np.random.randn(nchannels, freqs.shape[0])
    imag = scaling * np.random.randn(nchannels, freqs.shape[0])

    # If nsamples is even, at nyquist the FFT is real-valued only
    if not nsamples & 1:
        imag[-1] = 0.

    # IFFT the spectrum to obtain the time signal
    out = np.array(np.fft.irfft(real + 1j*imag),
                   ndmin=2, dtype='float32').T
    out /= np.abs(out).max(axis=0)
    return out
