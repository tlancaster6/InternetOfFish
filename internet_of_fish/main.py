import os.path
import sys, argparse
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from internet_of_fish.modules import runner, utils



def main(params):
    if utils.lights_on() or params.source:
        runner.active_mode(params)
    else:
        runner.passive_mode(params)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proj_id', help='project id')
    parser.add_argument('--model_id', help='name of the model')
    parser.add_argument('--kill_after', default=None, type=int, help='optional. kill after specified number of seconds')
    parser.add_argument('--source', default=None, type=str,
                        help='optional. pass a path to a video file to perform detection on that video, '
                             'rather than the camera stream')
    params = parser.parse_args()
    main(params)
