from queue import Empty
from threading import Thread
from multiprocessing import Event, Queue
import logging


logger = logging.getLogger(__name__)


class SinkThread(Thread):
    def __init__(self, running: Event, queue: Queue, rec_buffer: list) -> None:
        super().__init__(name="rtsSinkThread")
        logger.info(f"Initializing {self.name}")
        logger.debug(f"{running=}")
        logger.debug(f"{queue=}")
        logger.debug(f"{rec_buffer=}")
        self.queue = queue
        self.running = running
        self.rec_buffer = rec_buffer

    def run(self) -> None:
        logger.info(f"{self.name} running ...")
        logger.debug("Waiting for stream process start running.")
        self.running.wait()
        logger.debug(f"Starting {self.name} loop")
        while self.running.is_set():
            try:
                data = self.queue.get_nowait()
                self.rec_buffer.append(data)
            except Empty:
                self.rec_buffer.append(None)
        

