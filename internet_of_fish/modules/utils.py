import logging
import time, datetime
from internet_of_fish.modules import definitions
import os, socket, cv2

LOG_DIR, LOG_LEVEL = definitions.LOG_DIR, definitions.LOG_LEVEL
LOG_FMT = logging.Formatter(fmt='%(name)s %(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
os.makedirs(LOG_DIR, exist_ok=True)
logging.getLogger('PIL').setLevel(logging.WARNING)


def sleep_secs(max_sleep, end_time=999999999999999.9):
    """see mptools.sleep_secs()"""
    return max(0.0, min(end_time - time.time(), max_sleep))


def current_time_ms():
    """
    get milliseconds since last epoch as an integer. useful for generating unique filenames
    :return: ms since last epoch
    :rtype: int
    """
    return int(round(time.time() * 1000))


def current_time_iso():
    """
    get current date and time in human-readable iso format
    :return: iso formatted datetime
    :rtype: str
    """
    return datetime.datetime.now().isoformat(timespec='seconds')


def make_logger(name):
    """
    generate a logging.Logger object that writes to a file called "{name}.log". Logging level determined by
    definitions.LOG_LEVEL.
    :param name: logger name. Determines the name of the output file, and can also be used to access the logger via
                 logging.getLogger(name)
    :type name: str
    :return: pre-configured logger
    :rtype: logging.Logger
    """
    if not os.path.exists(definitions.LOG_DIR):
        os.makedirs(definitions.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        format='%(name)s %(asctime)s %(levelname)-8s %(message)s',
        level=LOG_LEVEL,
        datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()
    handler = logging.FileHandler(os.path.join(definitions.LOG_DIR, f'{name}.log'), mode='a')
    handler.setLevel(LOG_LEVEL)
    handler.setFormatter(LOG_FMT)
    logger.addHandler(handler)
    return logger


def lights_on(t=None):
    """
    checks if the current time fall within the valid recording timeframe, as specified by definitions.START_HOUR and
    definitions.END_HOUR.
    :param t: time to check. If None (default) the current time returned by datetime.datetime.now() is used
    :type t: datetime.datetime
    :return: True if t is within the valid recording timeframe, False otherwise
    :rtype: bool
    """
    if t is None:
        t = datetime.datetime.now()
    return definitions.START_HOUR <= t.hour < definitions.END_HOUR


def sleep_until_morning():
    """returns a positive sleep time, not exceeding the time until lights on (as specified by definitions.START_HOUR),
    but also no longer than 600 seconds. This function can be used to sleep a process for ten minute intervals until
    morning, with a relatively small margin of error.
    :return: time (in seconds) to sleep. Always less than 600 (10 minutes) and less than the time until START_HOUR
    :rtype: float
    """
    if lights_on():
        return 0
    curr_time = datetime.datetime.now()
    if curr_time.hour >= definitions.END_HOUR:
        curr_time = (curr_time + datetime.timedelta(days=1))
    next_start = curr_time.replace(hour=definitions.START_HOUR, minute=0, second=0, microsecond=0)
    return sleep_secs(600, next_start.timestamp())


def get_ip():
    """
    get the IP address of the current device.
    :return: device IP
    :rtype: str
    """
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


def jpgs_to_mp4(img_dir, dest_dir, fps=10):
    """create a video from a directory of images

    :param img_dir: folder containing images to combine into a video. Files should be named such that sorting
                    them alphanumerically puts them in the correct time order
    :type img_dir: str
    :param dest_dir: folder where the video will go
    :type dest_dir: str
    :param fps: framerate (frames per second) for the new video. Default 10
    :type fps: int
    :return vid_path: path to newly created video
    :rtype: str
    """
    imgs = sorted([img for img in os.listdir(img_dir) if img.endswith(".jpg")])
    frame = cv2.imread(os.path.join(img_dir, imgs[0]))
    height, width, layers = frame.shape
    vid_path = os.path.join(dest_dir, f'{os.path.splitext(imgs[0])[0]}.mp4')
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    video = cv2.VideoWriter(vid_path, fourcc, fps, (width, height))
    for img in imgs:
        video.write(cv2.imread(os.path.join(img_dir, img)))
    video.release()
    return vid_path


class Averager:

    def __init__(self):
        """
        efficient calculation of the mean of a growing dataset

        this lightweight class tracks the current mean (self.avg) and dataset size (self.count) of a growing dataset,
        without storing the entire dataset in memory. Useful, for example, for finding the average runtime of a process
        that repeats an undetermined number of times over a long period (which would otherwise require that we store
        every runtime value in a list or similar container until we were ready to calculate the final mean)
        """
        self.avg = None
        self.count = 0

    def update(self, val):
        """
        update the running mean (self.avg) according to val, and increment the count by one
        :param val: value that is being "appended" to the dataset
        :type val: float
        """
        if self.count == 0:
            self.avg = val
        else:
            self.avg = ((self.avg * self.count) + val) / (self.count + 1)
        self.count += 1
