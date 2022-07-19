from dataclasses import dataclass
from multiprocessing import Value
from multiprocessing.context import Process
from time import time, sleep
import logconfig
import  logging

logging.basicConfig(**logconfig.get())
logger = logging.getLogger(__name__)


class Configuration:
    _samplerate = Value('i', 48000)
    _blocksize = Value('i', 32)
    _inchannels = Value('i', 1)
    _outchannels = Value('i', 1)

    @classmethod
    def sampling_rate(cls) -> int:
        return cls._samplerate.value

    @classmethod
    def blocksize(cls) -> int:
        return cls._blocksize.value

    @classmethod
    def num_channels(cls) -> int:
        return cls._inchannels.value, cls._outchannels.value

    @classmethod
    def set_sampling_rate(cls, fs: int) -> None:
        cls._samplerate.value = fs

    @classmethod
    def set_blocksize(cls, bs: int) -> None:
        cls._blocksize.value = bs

    @classmethod
    def set_nchannels(cls, nc: int) -> None:
        cls._nchannels.value = nc


def collatz(num: int):
    return (num*3 + 1) if (num & 1) else (num//2)


class LoggerProcess(Process):

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        for _ in range(10):
            logging.info(f"{self.config.sampling_rate()=}")
            # logging.info(f"{self.config.blocksize()=}")
            # logging.info(f"{self.config.num_channels()=}")
            sleep(1.)

config = Configuration()

if __name__ == '__main__':

    p = LoggerProcess(config)

    p.start()
    for _ in range(30):
        logging.info(f"{collatz(config.sampling_rate())=}")
        config.set_sampling_rate(collatz(config.sampling_rate()))
        sleep(0.35)

    p.join()
    p.close()