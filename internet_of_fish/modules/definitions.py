import os

# filetree constants
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(MODULE_DIR)
BASE_DIR = os.path.dirname(CODE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, 'models')
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, '__ProjectData')

# project-specific parameters
TOPK = 3  # number of categories with highest score to display
CONF_THRESH = 0.1  # classifier score threshold
HIT_THRESH = 5  # hit counter threshold
WAIT_TIME = 1  # time between image captures in seconds
BATCHING_TIME = 60  # how long (in seconds) to accumulate images before running a

# hardware parameters
RESOLUTION = (1296, 972)  # pi camera resolution
FRAMERATE = 30  # pi camera framerate

# parameters for debugging/development
TESTING = False
VERBOSE = False
EXTRAVERBOSE = False