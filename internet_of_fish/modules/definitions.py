import os, logging, posixpath

# logging and debugging parameters
LOG_LEVEL = logging.INFO

# constant paths
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(MODULE_DIR)
BASE_DIR = os.path.dirname(CODE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
CREDENTIALS_DIR = os.path.join(BASE_DIR, 'credentials')
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, 'CichlidPiData', '__ProjectData')
CLOUD_HOME_DIR = 'cichlidVideo:BioSci-McGrath/Apps'
CLOUD_DATA_DIR = posixpath.join(CLOUD_HOME_DIR, 'CichlidPiData', '__ProjectData')
END_FILE = os.path.join(HOME_DIR, 'END')
SENDGRID_KEY_FILE = os.path.join(CREDENTIALS_DIR, 'sendgrid_key.secret')

# variable paths
PROJ_DIR = lambda proj_id: os.path.join(DATA_DIR, proj_id)
PROJ_VID_DIR = lambda proj_id: os.path.join(PROJ_DIR(proj_id), 'Videos')
PROJ_IMG_DIR = lambda proj_id: os.path.join(PROJ_DIR(proj_id), 'Images')
PROJ_LOG_DIR = lambda proj_id: os.path.join(PROJ_DIR(proj_id), 'Logs')



# project-specific parameters
MAX_FISH = 5  # maximum number of fish detections that should be returned
CONF_THRESH = 0.4  # classifier score threshold
HIT_THRESH = 10  # hit counter threshold
INTERVAL_SECS = 0.5  # time between image captures in seconds
IMG_BUFFER = int(10/INTERVAL_SECS)  # number of sequential images that will be sent if a spawning event is detected
START_HOUR = 8  # hour when data collection starts. e.g., if START_HOUR=8, collection starts at 8:00am
END_HOUR = 18  # hour when data collection ends. e.g., if END_HOUR=19, collection stops at 7:00pm
MAX_VIDEO_LEN = 3600 # max length of a video, in seconds. Set to (END_HOUR-START_HOUR)*3600 to record continuously
MIN_NOTIFICATION_INTERVAL = 600

# hardware parameters
RESOLUTION = (1296, 972)  # pi camera resolution
FRAMERATE = 30  # pi camera framerate

# app parameters. may be internally over-ridden by certain classes/processes
BOT_EMAIL = 'themcgrathlab@gmail.com'
MAX_UPLOAD_WORKERS = 3
MAX_TRIES = 3
DEFAULT_POLLING_TIMEOUT = 0.2
DEFAULT_MAX_SLEEP_SECS = 0.02
DEFAULT_INTERVAL_SECS = 10
DEFAULT_STARTUP_WAIT_SECS = 10
DEFAULT_SHUTDOWN_WAIT_SECS = 10