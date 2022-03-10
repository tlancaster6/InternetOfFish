import argparse
from modules.manager import Manager


parser = argparse.ArgumentParser()
parser.add_argument('--pid')
parser.add_argument('--model')
parser.add_argument('--iterlimit', default=None)
args = parser.parse_args()

manager = Manager(args.pid, args.model)
manager.collect_and_detect(args.iterlimit)
