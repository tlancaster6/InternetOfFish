import logging
import time, datetime
from internet_of_fish.modules import definitions
import os

log_level = logging.DEBUG
logging.getLogger('PIL').setLevel(logging.WARNING)
start_time = time.monotonic()

def _sleep_secs(max_sleep, end_time=999999999999999.9):
    # Calculate time left to sleep, no less than 0
    return max(0.0, min(end_time - time.time(), max_sleep))

def _logger(name, level, msg, exc_info=None):
    elapsed = time.monotonic() - start_time
    hours = int(elapsed // 60)
    seconds = elapsed - (hours * 60)
    logging.log(level, f'{hours:3}:{seconds:06.3f} {name:20} {msg}', exc_info=exc_info)

def _current_time_ms():
    return int(round(time.time() * 1000))

def _current_time_iso():
    return datetime.datetime.now().isoformat(timespec='seconds')

# def make_logger(name):
#     if not os.path.exists(definitions.LOG_DIR):
#         os.makedirs(definitions.LOG_DIR, exist_ok=True)
#     logging.basicConfig(
#         format='%(asctime)s %(levelname)-8s %(message)s',
#         level=log_level,
#         datefmt='%Y-%m-%d %H:%M:%S')
#     logger = logging.getLogger(name)
#     handler = logging.FileHandler(os.path.join(definitions.LOG_DIR, f'{name}.log'), mode='w')
#     handler.setLevel(log_level)
#     logger.addHandler(handler)
#     return logger


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
