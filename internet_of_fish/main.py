from modules import definitions
from modules.manager import Manager
import argparse
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

parser = argparse.ArgumentParser()
parser.add_argument('--pid')
parser.add_argument('--model')
args = parser.parse_args()

manager = Manager(args.pid, args.model)
manager.collect_and_detect()
