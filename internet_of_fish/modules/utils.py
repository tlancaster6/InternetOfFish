import logging
import time, datetime
from internet_of_fish.modules import definitions
import os, socket

LOG_DIR, LOG_LEVEL = definitions.LOG_DIR, definitions.LOG_LEVEL
os.makedirs(LOG_DIR, exist_ok=True)
logging.getLogger('PIL').setLevel(logging.WARNING)




def sleep_secs(max_sleep, end_time=999999999999999.9):
    # Calculate time left to sleep, no less than 0
    return max(0.0, min(end_time - time.time(), max_sleep))


def current_time_ms():
    return int(round(time.time() * 1000))


def current_time_iso():
    return datetime.datetime.now().isoformat(timespec='seconds')


def make_logger(name):
    if not os.path.exists(definitions.LOG_DIR):
        os.makedirs(definitions.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(name)
    handler = logging.FileHandler(os.path.join(definitions.LOG_DIR, f'{name}.log'), mode='w')
    handler.setLevel(LOG_LEVEL)
    logger.addHandler(handler)
    return logger


def sleep_until_morning():
    curr_time = datetime.datetime.now()
    next_start = (curr_time + datetime.timedelta(days=1))
    next_start = next_start.replace(hour=definitions.START_HOUR, minute=0, second=0, microsecond=0)
    if lights_on(curr_time):
        return 0.02
    return sleep_secs(600, (next_start - curr_time).total_seconds())


def lights_on(t=None):
    if t is None:
        t = datetime.datetime.now()
    return definitions.START_HOUR <= t.hour <= definitions.END_HOUR


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


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
