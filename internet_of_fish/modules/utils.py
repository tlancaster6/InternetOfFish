import logging
import time
from internet_of_fish.modules import definitions
import os
import sys

log_level = logging.DEBUG


def current_time_ms():
    return int(round(time.time() * 1000))


def make_logger(name):
    if not os.path.exists(definitions.LOG_DIR):
        os.makedirs(definitions.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=log_level,
        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(name)
    handler = logging.FileHandler(os.path.join(definitions.LOG_DIR, f'{name}.log'), mode='w')
    handler.setLevel(log_level)
    logger.addHandler(handler)
    return logger


def upload():
    pass


class Averager:

    def __init__(self):
        self.avg = None
        self.count = 0

    def update(self, val):
        if self.count == 0:
            self.avg = val
        else:
            self.avg = ((self.avg * self.count) + val) / (self.count + 1)
        self.count += 1
