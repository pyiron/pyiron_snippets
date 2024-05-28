"""
Set the logging level for pyiron
"""

import logging
from types import MethodType


def set_logging_level(self, level, channel=None):
    """
    Set level for logger

    Args:
        level (str): 'DEBUG, INFO, WARN'
        channel (int): 0: file_log, 1: stream, None: both
    """

    if channel:
        self.handlers[channel].setLevel(level)
    else:
        self.handlers[0].setLevel(level)
        self.handlers[1].setLevel(level)


def setup_logger():
    """
    Setup logger - logs are written to pyiron.log

    Returns:
        logging.getLogger: Logger
    """
    logger = logging.getLogger("pyiron_log")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARN)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    try:
        fh = logging.FileHandler("pyiron.log")
    except PermissionError:
        pass
    else:
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


logger = setup_logger()
logger.set_logging_level = MethodType(set_logging_level, logger)
