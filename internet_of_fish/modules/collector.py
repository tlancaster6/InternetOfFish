import logging
import multiprocessing
import queue

import picamera
import os
from internet_of_fish.modules import definitions
from internet_of_fish.modules.utils import current_time_ms, make_logger


def generate_vid_id(vid_dir):
    current_vids = [f for f in os.listdir(vid_dir) if (f.endswith('.h264') or f.endswith('.mp4'))]
    if len(current_vids) == 0:
        return('0001_vid')
    current_vids = [int(i) for i in [f.split('_')[0] for f in current_vids] if i.isdigit()]
    new_id = '{:04d}_vid'.format(max(current_vids) + 1)
    return new_id


class Collector:

    def __init__(self, vid_dir: str, img_dir: str):
        self.logger = make_logger('collector')
        self.logger.info('initializing Collector')
        self.definitions = definitions
        self.vid_dir, self.img_dir = vid_dir, img_dir
        self.running = False
        self.img_queue = multiprocessing.Queue()
        self.sig_queue = multiprocessing.Queue()
        self.stat_queue = multiprocessing.Queue()
        os.makedirs(img_dir)
        os.makedirs(vid_dir)

    def collect_data(self, vid_id=None):
        if vid_id is None:
            generate_vid_id(self.vid_dir)
        self.logger.info('initializing camera object')
        with picamera.PiCamera() as cam:
            self.logger.info('starting recording')
            cam.start_recording(os.path.join(self.vid_dir, f'{vid_id}.h264'))
            self.running = True
            while cam.recording:
                cam.wait_recording(self.definitions.WAIT_TIME)
                img_path = os.path.join(self.img_dir, f'{current_time_ms()}.jpg')
                cam.capture(img_path, use_video_port=True)
                self.logger.info(f'{img_path} captured')
                try:
                    self.img_queue.put(img_path)
                except queue.Full:
                    self.logger.warn('img_queue full, cannot add path to queue')
                if not self.sig_queue.empty():
                    sig = self.sig_queue.get()
                    if sig == 'STOP':
                        break

        self.logger.info('exiting data collection')
        self.running = False
