import multiprocessing as mp
import os, time, sys, datetime
from glob import glob

from internet_of_fish.modules import definitions
from internet_of_fish.modules.detector import start_detection_mp
from internet_of_fish.modules.collector import start_collection_mp
from internet_of_fish.modules.utils import make_logger

class Manager:

    def __init__(self, project_id, model):
        self.logger = make_logger('manager')
        self.logger.info('initializing manager')
        self.definitions = definitions

        self.project_id, self.model = project_id, model
        self.vid_dir = os.path.join(definitions.DATA_DIR, project_id, 'Videos')
        self.img_dir = os.path.join(definitions.DATA_DIR, project_id, 'Images')

        self.img_queue = mp.Queue()
        self.shutdown_event = mp.Event()

        self.detection_process = None
        self.collection_process = None

    @staticmethod
    def locate_model_files(model):
        try:
            model_path = glob(os.path.join(definitions.MODELS_DIR, model, '*.tflite'))[0]
            label_path = glob(os.path.join(definitions.MODELS_DIR, model, '*.txt'))[0]
            return model_path, label_path
        except IndexError as e:
            print(f'error locating model files:\n{e}')

    def collect_and_detect(self, iterlimit=None):
        """run simultaneous collection and detection"""
        self.start_collection()
        self.start_detection()
        iters = 0
        while 8 <= datetime.datetime.now().hour <= 18:
            if iterlimit is not None and iters > iterlimit:
                self.logger.debug('max iters reached, exiting loop collect and detect loop')
                break
            try:
                time.sleep(10)
                self.collection_process.join(timeout=1)
                self.detection_process.join(timeout=1)
            except KeyboardInterrupt:
                print('shutting down detection process')
                self.stop_collection()
                print('shutting down collection process')
                self.stop_detection()
                print('processing and uploading last video')
                self.process_video()
                self.upload_video()
                print('exiting')
                sys.exit()
            iters += 1
            self.logger.debug(f'manager iters = {iters}')
        self.shutdown()
        self.process_video()
        self.upload_video()

        while not 7 <= datetime.datetime.now().hour <= 18:
            time.sleep(3600)
        while not 7 <= datetime.datetime.now().hour <= 18:
            time.sleep(1)

        if iterlimit is None:
            self.collect_and_detect()

    def start_collection(self):
        """start collection as a multiprocessing Process"""
        self.logger.info('starting collection')
        self.collection_process = mp.Process(target=start_collection_mp,
                                             args=(self.vid_dir, self.img_dir, self.img_queue,
                                                   self.shutdown_event))
        self.collection_process.start()
        return self.collection_process

    def start_detection(self):
        """start detection as a multiprocessing Process"""
        self.logger.info('starting detection')
        self.detection_process = mp.Process(target=start_detection_mp,
                                            args=(*self.locate_model_files(self.model),
                                                  self.img_queue, self.shutdown_event))
        self.detection_process.start()
        return self.detection_process

    def shutdown(self):
        self.shutdown_event.set()

    def get_next_vid_id(self):
        """generates a new video id (0001_vid, 0002_vid, etc) based on the videos already uploaded to Dropbox"""
        # TODO: write this function
        pass

    def process_video(self):
        """converts any .h264 videos in the video directory to .mp4"""
        # TODO: write this function
        pass

    def upload_video(self):
        """upload any .mp4 videos in the video directory to Dropbox"""
        # TODO: write this function
        pass


if __name__ == '__main__':
    mp.set_start_method('spawn')
