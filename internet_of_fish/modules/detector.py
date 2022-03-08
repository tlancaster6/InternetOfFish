import os
import time

from PIL import Image
from PIL import ImageDraw
from glob import glob

from pycoral.adapters import common
from pycoral.adapters import detect
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter

import definitions
from utils import make_logger


class HitCounter:

    def __init__(self):
        self.hits = 0

    def increment(self):
        self.hits += 1

    def decrement(self):
        if self.hits > 0:
            self.hits -= 1

    def reset(self):
        self.hits = 0


class Detector:

    def __init__(self, model_path, label_path):
        self.logger = make_logger('detector')
        self.logger.info('initializing detector')
        self.interpreter = make_interpreter(model_path)
        self.labels = read_label_file(label_path)
        self.ids = {val: key for key, val in self.labels.items()}
        self.hit_counter = HitCounter()
        self.running = False

    def detect(self, img_path):
        """run detection on a single image"""
        image = Image.open(img_path)
        _, scale = common.set_resized_input(
            self.interpreter, image.size, lambda size: image.resize(size, Image.ANTIALIAS))
        self.interpreter.invoke()
        dets = detect.get_objects(self.interpreter, definitions.CONF_THRESH, scale)
        return dets

    def overlay_boxes(self, img_path, dets):
        """open an image, draw detection boxes, and replace the original image"""
        img = Image.open(img_path).convert('RGB')
        draw = ImageDraw.Draw(img)
        for det in dets:
            bbox = det.bbox
            draw.rectangle([(bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax)],
                           outline='red')
            draw.text((bbox.xmin + 10, bbox.ymin + 10),
                      '%s\n%.2f' % (self.labels.get(det.id, det.id), det.score),
                      fill='red')
        img.save(img_path)

    def check_for_hit(self, dets):
        """check for multiple fish intersecting with the pipe and adjust hit counter accordingly"""
        fish_bboxes = [d.bbox for d in dets if d.id == self.ids['fish']]
        pipe_bbox = [d.bbox for d in dets if d.id == self.ids['pipe']]
        if (len(fish_bboxes) < 2) or (len(pipe_bbox) != 1):
            self.hit_counter.decrement()
            return False
        intersect_count = 0
        for bbox in fish_bboxes:
            intersect = detect.BBox.intersect(bbox, pipe_bbox)
            intersect_count += intersect.valid
        if intersect_count < 2:
            self.hit_counter.decrement()
            return False
        else:
            self.hit_counter.increment()
            return True

    def notify(self):
        # TODO: write notification function
        pass

    def batch_detect(self, img_dir):
        """continuously run detection on batches as files are added to img_dir"""
        self.logger.info('continuous detection starting in batch mode')
        self.running = True
        while self.running:
            start = time.time()
            img_paths = [glob(os.path.join(img_dir, '*.jpg'))]
            img_paths.sort()
            for p in img_paths:
                dets = self.detect(p)
                self.check_for_hit(dets)
            self.logger.info(f'batch detection completed. Processed {len(img_paths)} frames in {time.time()-start} seconds')
            if self.hit_counter.hits >= definitions.HIT_THRESH:
                self.logger.info('POSSIBLE SPAWNING EVENT DETECTED')
                self.notify()
            for p in img_paths:
                os.remove(p)
                time.sleep(definitions.BATCHING_TIME)
        self.logger.info('continuous detection exiting')

    def queue_detect(self, queue):
        """continuously run detection on images in the order their paths are added to the multiprocessing queue"""
        self.logger.info('continuous detection starting in queue mode')
        self.running = True
        img_buffer = []
        while self.running:
            img_path = queue.get()
            img_buffer.append(img_path)
            dets = self.detect(img_path)
            self.check_for_hit(dets)
            if self.hit_counter.hits >= definitions.HIT_THRESH:
                self.logger.info('POSSIBLE SPAWNING EVENT DETECTED')
                self.notify()
            if len(img_buffer) > definitions.IMG_BUFFER:
                os.remove(img_buffer.pop(0))
            while queue.empty():
                self.logger.info('queue empty, sleeping for 60 seconds')
                time.sleep(60)
        self.logger.info('continuous detection exiting')

    def stop(self):
        self.running = False


