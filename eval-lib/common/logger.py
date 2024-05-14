import sys
import os
import logging
from logging import FileHandler
from logging import StreamHandler

LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARN,
    "error": logging.ERROR,
}


class LoggerManager(object):

    LOGGER = logging.getLogger('root')

    def __init__(self, log_level="debug", log_file="/root/log"):
        self.log_level = log_level
        self.log_file = log_file
        self.formatter = logging.Formatter(
            '%(asctime)s T%(thread)d-%(threadName)s '
            '%(levelname)s %(module)s.'
            '%(funcName)s.%(lineno)s: %(message)s'
        )
        self.init_logger()

    @property
    def stdout_handler(self):
        stdout_handler = StreamHandler(sys.stdout)
        stdout_handler.setFormatter(self.formatter)
        return stdout_handler

    @classmethod
    def get_logger(cls):
        return cls.LOGGER

    def get_child_logger(
        self, name='root', log_level='debug', log_file="", propagate=True
    ):
        logger = logging.getLogger(name)
        logger.propagate = propagate
        logger.setLevel(LOG_LEVEL_MAP.get(log_level))
        if log_file:
            file_handler = FileHandler(log_file)
            file_handler.setFormatter(self.formatter)
            logger.addHandler(file_handler)
        logger.addHandler(self.stdout_handler)
        return logger

    def init_logger(self):
        if len(self.LOGGER.handlers) > 0:
            return
        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.LOGGER.setLevel(LOG_LEVEL_MAP.get(self.log_level))
        if self.log_file:
            file_handler = FileHandler(self.log_file)
            file_handler.setFormatter(self.formatter)
            self.LOGGER.addHandler(file_handler)
        self.LOGGER.addHandler(self.stdout_handler)


def get_logger():
    return LoggerManager.get_logger()
