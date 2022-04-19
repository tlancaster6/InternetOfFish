import os, logging, posixpath

# constant paths
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(MODULE_DIR)
BASE_DIR = os.path.dirname(CODE_DIR)
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
SUMMARY_LOG_FILE = os.path.join(LOG_DIR, 'SUMMARY.log')
CREDENTIALS_DIR = os.path.join(BASE_DIR, 'credentials')
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, 'CichlidPiData', '__ProjectData')
CLOUD_HOME_DIR = 'cichlidVideo:/BioSci-McGrath/Apps'
CLOUD_DATA_DIR = posixpath.join(CLOUD_HOME_DIR, 'CichlidPiData', '__ProjectData')
END_FILE = os.path.join(HOME_DIR, 'ENTER_END_MODE')
PAUSE_FILE = os.path.join(HOME_DIR, 'HARD_SHUTDOWN')
SENDGRID_KEY_FILE = os.path.join(CREDENTIALS_DIR, 'sendgrid_key.secret')

# variable paths
PROJ_DIR = lambda proj_id: os.path.join(DATA_DIR, proj_id)
PROJ_VID_DIR = lambda proj_id: os.path.join(PROJ_DIR(proj_id), 'Videos')
PROJ_IMG_DIR = lambda proj_id: os.path.join(PROJ_DIR(proj_id), 'Images')
PROJ_LOG_DIR = lambda proj_id: os.path.join(PROJ_DIR(proj_id), 'Logs')
PROJ_JSON_FILE = lambda proj_id: os.path.join(PROJ_DIR(proj_id), f'{proj_id}.json')

