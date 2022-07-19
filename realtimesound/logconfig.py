import logging


def get() -> dict:
    return dict(
        level=logging.DEBUG,
        format="%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
        handlers=[
            logging.FileHandler(f"{__file__.replace('.py', '.log')}"),
            logging.StreamHandler()
        ]
    )
