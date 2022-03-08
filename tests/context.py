import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from internet_of_fish.modules.collector import Collector, generate_vid_id
from internet_of_fish.modules.detector import Detector, HitCounter
from internet_of_fish.modules.manager import Manager


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.join(TEST_DIR, 'resources')
TMP_DIR = os.path.join(TEST_DIR, 'tmp')
MODEL_DIR = os.path.join(RESOURCES_DIR, 'test_model')
