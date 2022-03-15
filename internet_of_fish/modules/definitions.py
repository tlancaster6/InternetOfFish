import os, logging

LOG_LEVEL = logging.DEBUG

# filetree constants
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(MODULE_DIR)
BASE_DIR = os.path.dirname(CODE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, 'CichlidPiData', '__ProjectData')

# project-specific parameters
MAX_FISH = 5  # maximum number of fish detections that should be returned
CONF_THRESH = 0.4  # classifier score threshold
HIT_THRESH = 10  # hit counter threshold
INTERVAL_SECS = 0.5  # time between image captures in seconds
IMG_BUFFER = 100  # number of sequential images that will be sent if a spawning event is detected in queue mode

# hardware parameters
RESOLUTION = (1296, 972)  # pi camera resolution
FRAMERATE = 30  # pi camera framerate
