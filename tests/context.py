import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from internet_of_fish.modules.collector import Collector, generate_vid_id
from internet_of_fish.modules.detector import Detector
from internet_of_fish.modules.manager import Manager


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(TEST_DIR, 'test_data')
TMP_DIR = os.path.join(TEST_DIR, 'tmp')