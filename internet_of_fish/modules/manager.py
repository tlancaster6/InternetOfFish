import multiprocessing as mp
import os, time, sys, datetime
from glob import glob

from internet_of_fish.modules import definitions
from internet_of_fish.modules.detector import Detector, start_detection_mp
from internet_of_fish.modules.collector import Collector, start_collection_mp
from internet_of_fish.modules.utils import make_logger


class Manager:

    def __init__(self, project_id, model):
        self.logger = make_logger('manager')
        self.logger.info('initializing manager')

        self.project_id, self.model = project_id, model
        self.vid_dir = os.path.join(definitions.DATA_DIR, project_id, 'Videos')
        self.img_dir = os.path.join(definitions.DATA_DIR, project_id, 'Images')
        self.img_queue = mp.Queue()
        self.collector_sig_queue = mp.Queue()

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
        self.start_collection()
        self.start_detection()
        iters = 0
        while (self.collection_process is not None) or (self.detection_process is not None):
            try:
                time.sleep(10)
                self.collection_process.join(timeout=0)
                self.detection_process.join(timeout=0)
            except KeyboardInterrupt:
                print('shutting down detection process')
                self.stop_detection()
                print('shutting down collection process')
                self.stop_collection()
                print('exiting')
                sys.exit()
            if (not 8 <= datetime.datetime.now().hour <= 18) or (iterlimit is not None and iters > iterlimit):
                self.stop_detection()
                self.stop_collection()
            iters += 1
            self.logger.debug(f'managers iters = {iters}')

    def start_collection(self):
        self.logger.info('starting collection')
        self.collection_process = mp.Process(target=start_collection_mp,
                                             args=(self.vid_dir, self.img_dir, self.img_queue, self.collector_sig_queue))
        self.collection_process.start()
        return self.collection_process

    def start_detection(self):
        self.logger.info('starting detection')
        # detection_process = mp.Process(target=self.detector.batch_detect, args=(self.img_dir,))
        self.detection_process = mp.Process(target=start_detection_mp,
                                            args=(*self.locate_model_files(self.model), self.img_queue,))
        self.detection_process.start()
        return self.detection_process

    def stop_detection(self):
        """add a 'STOP' the detector's image queue, which will trigger the detection to exit elegantly"""
        if self.detection_process is None:
            self.logger.info('manager.stop_detection called, but no detection process was running')
            return
        self.img_queue.put('STOP')
        self.detection_process.join()
        self.detection_process = None

    def stop_collection(self):
        """add a 'STOP' the collector's signal queue, which will trigger the collection to exit elegantly"""
        if self.collection_process is None:
            self.logger.info('manager.stop_collection called, but no collection process was running')
            return
        self.collector_sig_queue.put('STOP')
        self.collection_process.join()
        self.collection_process = None


if __name__ == '__main__':
    mp.set_start_method('spawn')
