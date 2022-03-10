import os

# filetree constants
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(MODULE_DIR)
BASE_DIR = os.path.dirname(CODE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, 'CichlidPiData', '__ProjectData')

# project-specific parameters
MAX_FISH = 3  # maximum number of fish detections that should be returned
CONF_THRESH = 0.1  # classifier score threshold
HIT_THRESH = 5  # hit counter threshold
WAIT_TIME = 1  # time between image captures in seconds
BATCHING_TIME = 60  # how long (in seconds) to accumulate images before running a
IMG_BUFFER = 10  # number of sequential images that will be sent if a spawning event is detected in queue mode

# hardware parameters
RESOLUTION = (1296, 972)  # pi camera resolution
FRAMERATE = 30  # pi camera framerate
