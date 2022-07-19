from queue import Empty, Full
from threading import Thread
from multiprocessing import Event, Queue
from audio import AudioGenerator
import logging
import numpy as np


logger = logging.getLogger(__name__)


class SourceThread(Thread):
    def __init__(self, running: Event, queue: Queue, play_buffer: AudioGenerator) -> None:
        super().__init__(name="rtsSourceThread")
        logger.info(f"Initializing {self.name}")
        logger.debug(f"{running=}")
        logger.debug(f"{queue=}")
        self.queue = queue
        self.running = running
        self.buffer = play_buffer


    def run(self) -> None:
        logger.info(f"{self.name} running ...")
        logger.debug("Waiting for stream process start running.")
        self.running.wait()
        logger.debug(f"Starting {self.name} loop")
        while self.running.is_set():
            try:
                self.queue.put_nowait(next(self.buffer))
            except Full:
                pass
            except (StopIteration, StopAsyncIteration):
                self.queue.put_nowait(np.zeros((self.buffer.size, self.buffer.channels)))
        

