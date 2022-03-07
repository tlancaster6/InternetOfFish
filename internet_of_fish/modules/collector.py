import picamera
import os
import definitions
from utils import current_time_ms, vprint, vvprint


def generate_vid_id(vid_dir):
    vprint('generating new video id')
    current_vids = [f for f in os.listdir(vid_dir) if (f.endswith('.h264') or f.endswith('.mp4'))]
    if len(current_vids) == 0:
        return('0001_vid')
    current_vids = [int(i) for i in ['_'.split(f)[0] for f in current_vids] if i.isdigit()]
    new_id = '{:02d}_vid'.format(max(current_vids) + 1)
    vprint(f'video id generaged: {new_id}')
    return new_id


class Collector:

    def __init__(self, vid_dir, img_dir):
        vprint('initializing Collector')
        self.vid_dir, self.img_dir = vid_dir, img_dir
        self.camera = picamera.PiCamera()
        self.camera.resolution = definitions.RESOLUTION
        self.camera.framerate = definitions.FRAMERATE
        self.running = False
        os.makedirs(img_dir)
        os.makedirs(vid_dir)
        vprint('Collector initialized')

    def collect_data(self, vid_id=None):
        if vid_id is None:
            generate_vid_id(self.vid_dir)
        vprint('starting recording')
        self.camera.start_recording(os.path.join(self.vid_dir, f'{vid_id}.h264'))
        self.running = True
        while self.camera.recording:
            self.camera.wait_recording(definitions.WAIT_TIME)
            self.camera.capture(os.path.join(self.img_dir, f'{current_time_ms()}.jpg'), use_video_port=True)
            vvprint(f'{current_time_ms()}.jpg captured')
        vprint('exiting data collection')
        self.running = False
