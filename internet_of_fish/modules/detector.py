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
from utils import vprint, vvprint


class HitCounter:

    def __init__(self):
        vprint('initializing hit detector')
        self.hits = 0

    def increment(self):
        self.hits += 1
        vprint(f'hit counter incremented. Current value {self.hits}')

    def decrement(self):
        if self.hits > 0:
            self.hits -= 1

    def reset(self):
        self.hits = 0


class Detector:

    def __init__(self, model_path, label_path):
        vprint('initializing Detector')
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
        start = time.perf_counter()
        self.interpreter.invoke()
        inference_time = time.perf_counter() - start
        dets = detect.get_objects(self.interpreter, definitions.CONF_THRESH, scale)
        vvprint('inference time: {:.2f} ms'.format(inference_time * 1000))
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

    def continuous_detect(self, img_dir):
        """continuously run detection on batches"""
        vprint('continuous detection starting')
        self.running = True
        while self.running:
            start = time.time()
            img_paths = [glob(os.path.join(img_dir, '*.jpg'))]
            img_paths.sort()
            for p in img_paths:
                dets = self.detect(p)
                self.check_for_hit(dets)
            vprint(f'batch detection completed. Processed {len(img_paths)} frames in {time.time()-start} seconds')
            if self.hit_counter.hits >= definitions.HIT_THRESH:
                vprint('POSSIBLE SPAWNING EVENT DETECTED')
                pass
                #TODO: notification call here
            for p in img_paths:
                os.remove(p)
                time.sleep(definitions.BATCHING_TIME)
        vprint('continuous detection exiting')

    def stop(self):
        self.running = False


