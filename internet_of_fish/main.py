import os.path
import sys, argparse
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from internet_of_fish.modules import runner, utils, metadata


def main(args):
    try:
        metadata_handler = metadata.MetaDataHandler(new_proj=args.new_proj, kill_after=args.kill_after, source=args.source)
        metadata_simple = metadata_handler.simplify()
        if utils.lights_on() or args.source:
            runner.active_mode(metadata_simple)
        else:
            runner.passive_mode(metadata_simple)
    except KeyboardInterrupt:
        print('Keyboard Interrupt Detected. Exiting')
        sys.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--new_proj', action='store_true',
                        help='indicates that a new project should be created. If this flag is omitted, the most'
                             'recently created project that is present on this device will be resumed')
    parser.add_argument('--kill_after', default=None, type=int,
                        help='optional. kill after specified number of seconds. If None (default) the app will run '
                             'continuously until it encounters a fatal error or is otherwise forced to shut down')
    parser.add_argument('--source', default=None, type=str,
                        help='optional. pass a path to a video file to perform detection on that video, '
                             'rather than the camera stream. If None (default) the camera stream is used.')
    args_ = parser.parse_args()
    main(args_)
