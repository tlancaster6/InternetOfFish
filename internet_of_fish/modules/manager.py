import multiprocessing as mp
import definitions
import os

from detector import Detector
from collector import Collector
from utils import make_logger

class Manager:

    def __init__(self, vid_dir, img_dir, model_path, label_path):
        self.logger = make_logger('Manager')
        self.logger.info('initializing manager')
        self.img_dir, self.vid_dir = img_dir, vid_dir

        self.collector = Collector(vid_dir, img_dir)
        self.detector = Detector(model_path, label_path)

    def collect_and_detect(self):
        collection_process = self.start_collection()
        detection_process = self.start_detection()

    def start_collection(self):
        self.logger.info('starting collection')
        collection_process = mp.Process(target=self.collector.collect_data, kwargs={'queue': self.img_queue})
        collection_process.start()
        return collection_process


    def start_detection(self):
        self.logger.info('starting detection')
        # detection_process = mp.Process(target=self.detector.batch_detect, args=(self.img_dir,))
        detection_process = mp.Process(target=self.detector.queue_detect, args=(self.img_queue,))
        detection_process.start()
        return detection_process

    def stop_detection(self):
        """add a 'STOP' the detector's image queue, which will trigger the detection to exit elegantly"""
        self.detector.img_queue.put('STOP')

    def stop_collection(self):
        """add a 'STOP' the collector's signal queue, which will trigger the collection to exit elegantly"""
        self.collector.sig_queue.put('STOP')
