import argparse
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.manager import Manager

"""
python3 main.py --pid test_project --model mobilenetv2 
"""


parser = argparse.ArgumentParser()
parser.add_argument('--pid', help='project id')
parser.add_argument('--model', help='name of the model')
parser.add_argument('--iterlimit', default=None, type=int)
args = parser.parse_args()

manager = Manager(args.pid, args.model)
manager.collect_and_detect(args.iterlimit)
