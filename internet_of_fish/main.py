from modules import definitions
from modules.manager import Manager
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--pid')
parser.add_argument('--model')
args = parser.parse_args()

manager = Manager(args.pid, args.model)
manager.collect_and_detect()
