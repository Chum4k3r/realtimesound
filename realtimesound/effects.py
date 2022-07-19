import numpy as np


def compress(sound: np.ndarray, threshold: float, ratio: float):
    lower = np.where(sound < threshold, (sound + threshold) * ratio - threshold, sound)
    total = np.where(sound > threshold, (sound - threshold) * ratio + threshold, lower)
    return total


def distort(sound):
    return np.arcsin(np.clip(sound, -1, 1))
