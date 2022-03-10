import multiprocessing
import os
import time

from PIL import Image
from PIL import ImageDraw

from pycoral.adapters import common
from pycoral.adapters import detect
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter

from internet_of_fish.modules import definitions
from internet_of_fish.modules.utils import make_logger, Averager


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

    def __init__(self, model_path, label_path, img_queue: multiprocessing.Queue):
        self.logger = make_logger('detector')
        self.logger.info('initializing detector')
        self.interpreter = make_interpreter(model_path)
        self.interpreter.allocate_tensors()
        self.labels = read_label_file(label_path)
        self.ids = {val: key for key, val in self.labels.items()}
        self.hit_counter = HitCounter()
        self.running = False
        self.img_queue = img_queue
        self.avg_timer = Averager()


    def detect(self, img_path):
        """run detection on a single image"""
        start = time.time()
        image = Image.open(img_path)
        self.logger.debug('setting resized input')
        _, scale = common.set_resized_input(
            self.interpreter, image.size, lambda size: image.resize(size, Image.ANTIALIAS))
        self.logger.debug('invoking interpreter')
        self.interpreter.invoke()
        self.logger.debug('performing inference')
        dets = detect.get_objects(self.interpreter, definitions.CONF_THRESH, scale)
        duration = time.time() - start
        self.avg_timer.update(duration)
        self.logger.debug(f'inference performed on {os.path.split(img_path)[-1]} in {duration}')
        confs = [det.score for det in dets]
        self.logger.debug(f'max score of {max(confs)}, min score of {min(confs)}')
        return dets

    def overlay_boxes(self, img_path, dets):
        """open an image, draw detection boxes, and replace the original image"""
        self.logger.debug(f'overalying boxes on {os.path.split(img_path)[-1]}')
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

    def check_for_hit(self, fish_dets, pipe_det):
        """check for multiple fish intersecting with the pipe and adjust hit counter accordingly"""
        if (len(fish_dets) < 2) or (len(pipe_det) != 1):
            self.hit_counter.decrement()
            return False
        intersect_count = 0
        pipe_det = pipe_det[0]
        self.logger.debug(f'checking {fish_dets}) against {pipe_det}')
        for det in fish_dets:
            intersect = detect.BBox.intersect(det.bbox, pipe_det.bbox)
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

    def queue_detect(self):
        """continuously run detection on images in the order their paths are added to the multiprocessing queue"""
        self.logger.info('continuous detection starting in queue mode')
        self.running = True
        img_buffer = []
        dets_buffer = []
        while self.running:
            self.logger.debug('waiting for image')
            img_path = self.img_queue.get()
            fname = os.path.split(img_path)[-1]
            self.logger.debug(f'image path aquired from queue: {fname}')
            if img_path == 'STOP':
                self.logger.info('stop signal encountered, exiting detection')
                break
            img_buffer.append(img_path)
            dets = self.detect(img_path)
            self.logger.debug(f'detection complete for {fname}. {len(dets)} detections')
            fish_dets, pipe_det = self.filter_dets(dets)
            dets_buffer.append(fish_dets+pipe_det)
            self.check_for_hit(fish_dets, pipe_det)
            self.logger.debug(f'hit check complete for {fname}. current hit count: {self.hit_counter.hits}')
            if self.hit_counter.hits >= definitions.HIT_THRESH:
                self.logger.info('POSSIBLE SPAWNING EVENT DETECTED')
                [self.overlay_boxes(i, d) for i, d in zip(img_buffer, dets_buffer)]
                self.notify()
            if len(img_buffer) > definitions.IMG_BUFFER:
                os.remove(img_buffer.pop(0))
                dets_buffer.pop(0)
        self.logger.info('continuous detection exiting')
        if self.avg_timer.avg is not None:
            self.logger.info(f'average inference time: {self.avg_timer.avg / 1000}ms')
        else:
            self.logger.info('cannot calculate inference time because detection never ran successfully')
        [self.overlay_boxes(i, d) for i, d in zip(img_buffer, dets_buffer)]
        self.running = False

    def filter_dets(self, dets):
        fish_dets = [d for d in dets if d.id == self.ids['fish']][:definitions.MAX_FISH]
        pipe_det = [d for d in dets if d.id == self.ids['pipe']][:1]
        self.logger.debug(f'detections filtered. {len(fish_dets)} fish detections '
                          f'and {len(pipe_det)} pipe detections found')
        return fish_dets, pipe_det

def start_detection_mp(model_path, label_path, img_queue: multiprocessing.Queue):
    detector = Detector(model_path, label_path, img_queue)
    detector.queue_detect()


