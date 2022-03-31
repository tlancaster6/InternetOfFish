import os, logging, posixpath

# logging and debugging parameters
LOG_LEVEL = logging.DEBUG

# filetree constants
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(MODULE_DIR)
BASE_DIR = os.path.dirname(CODE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, 'CichlidPiData', '__ProjectData')
CLOUD_HOME_DIR = 'cichlidVideo:BioSci-McGrath/Apps'
CLOUD_DATA_DIR = posixpath.join(CLOUD_HOME_DIR, 'CichlidPiData', '__ProjectData')

# project-specific parameters
MAX_FISH = 5  # maximum number of fish detections that should be returned
CONF_THRESH = 0.4  # classifier score threshold
HIT_THRESH = 10  # hit counter threshold
INTERVAL_SECS = 0.5  # time between image captures in seconds
IMG_BUFFER = int(10/INTERVAL_SECS)  # number of sequential images that will be sent if a spawning event is detected
START_HOUR = 8  # hour when data collection starts. e.g., if START_HOUR=8, collection starts at 8:00am
END_HOUR = 13  # hour when data collection ends. e.g., if END_HOUR=19, collection stops at 7:00pm

# hardware parameters
RESOLUTION = (1296, 972)  # pi camera resolution
FRAMERATE = 30  # pi camera framerate
