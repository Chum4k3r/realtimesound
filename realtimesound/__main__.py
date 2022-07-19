from multiprocessing import Event, freeze_support, Manager, Queue
from typing import Generator
from realtimesound import logconfig
from realtimesound.noisegenerator import noise_generator
assert logconfig
from realtimesound.threads.sink import SinkThread
from realtimesound.threads.source import SourceThread
import logging
import numpy as np


logger = logging.getLogger(__name__)



def main(src: SourceThread, snk: SinkThread, running: Event) -> None:
    logger.debug("Starting main func")
    src.start()
    logger.debug("Started source thread")
    snk.start()
    logger.debug("Started sink thread")

    request_quit = False
    print("Starting realtimesound server")
    running.set()
    while not request_quit:
        command = input("-->  ")
        if command.upper() in ['EXIT', 'QUIT', 'FINISH', 'TERMINATE', 'CLOSE']:
            request_quit = True

    src.join(timeout=3.)
    snk.join(timeout=3.)


if __name__ == '__main__':
   freeze_support()

   with Manager() as manager:
        # sinkQu: Queue = manager.Queue()
        # sourceQu: Queue = manager.Queue()

        running = manager.Event()

        buffer = manager.list()

        aQu: Queue = manager.Queue()

        sink = SinkThread(running, aQu, buffer)

        source = SourceThread(running, aQu, noise_generator())

        main(source, sink, running)

        print(buffer)
