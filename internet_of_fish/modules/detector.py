import os, logging, time
from collections import namedtuple

from PIL import Image, ImageDraw
from glob import glob

from pycoral.adapters import common
from pycoral.adapters import detect
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter

from internet_of_fish.modules import definitions, mptools, utils

BufferEntry = namedtuple('BufferEntry', ['cap_time', 'img', 'dets'])

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


class DetectorWorker(mptools.QueueProcWorker):
    MODELS_DIR = definitions.MODELS_DIR
    DATA_DIR = definitions.DATA_DIR
    MAX_FISH = definitions.MAX_FISH
    HIT_THRESH = definitions.HIT_THRESH
    IMG_BUFFER = definitions.IMG_BUFFER

    def init_args(self, args):
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.init_args : {args}")
        self.img_q, = args
        self.work_q = self.img_q  # renaming to clarify that, for this class, the work queue is always the img queue
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.init_args")

    def startup(self):
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.startup")
        self.img_dir = os.path.join(self.DATA_DIR, self.params.proj_id, 'Images')
        os.makedirs(self.img_dir, exist_ok=True)

        model_path = glob(os.path.join(self.MODELS_DIR, self.params.model_id, '*.tflite'))[0]
        label_path = glob(os.path.join(self.MODELS_DIR, self.params.model_id, '*.txt'))[0]
        self.interpreter = make_interpreter(model_path)
        self.interpreter.allocate_tensors()

        self.labels = read_label_file(label_path)
        self.ids = {val: key for key, val in self.labels.item_dict()}

        self.hit_counter = HitCounter()
        self.avg_timer = utils.Averager()
        self.buffer = []
        self.active = True
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.startup")

    def main_func(self, q_item):
        if not self.active:
            time.sleep(1)
            return
        if (type(q_item) == str) and (q_item == 'SHUTDOWN'):
            self.logger.log(logging.INFO, 'Detector entering sleep mode (SHUTDOWN trigger encountered in img_q)')
            self.event_q.safe_put(mptools.EventMessage(self.name, 'SHUTDOWN', 'SHUTDOWN trigger encountered in img_q'))
            self.active = False
            return
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.main_func")
        cap_time, img = q_item
        dets = self.detect(img)
        fish_dets, pipe_det = self.filter_dets(dets)
        self.buffer.append(BufferEntry(cap_time, img, fish_dets + pipe_det))
        self.check_for_hit(fish_dets, pipe_det)
        if self.hit_counter.hits >= self.HIT_THRESH:
            self.logger.log(logging.INFO, f"Hit threshold of {self.HIT_THRESH} exceeded, possible spawning event")
            [self.overlay_boxes(be) for be in self.buffer]
            self.notify()
            self.hit_counter.reset()
        if len(self.buffer) > self.IMG_BUFFER:
            self.buffer.pop(0)
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.main_func")

    def detect(self, img):
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.detect")
        """run detection on a single image"""
        start = time.time()
        _, scale = common.set_resized_input(
            self.interpreter, img.size, lambda size: img.resize(size, Image.ANTIALIAS))
        self.interpreter.invoke()
        dets = detect.get_objects(self.interpreter, definitions.CONF_THRESH, scale)
        self.avg_timer.update(time.time() - start)
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.detect")
        return dets

    def overlay_boxes(self, buffer_entry: BufferEntry):
        """open an image, draw detection boxes, and replace the original image"""
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.overlay_boxes")
        draw = ImageDraw.Draw(buffer_entry.img)
        for det in buffer_entry.dets:
            bbox = det.bbox
            draw.rectangle([(bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax)],
                           outline='red')
            draw.text((bbox.xmin + 10, bbox.ymin + 10),
                      '%s\n%.2f' % (self.labels.get(det.id, det.id), det.score),
                      fill='red')
        buffer_entry.img.save(os.path.join(self.img_dir, f'{buffer_entry.cap_time}.jpg'))
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.overlay_boxes")

    def check_for_hit(self, fish_dets, pipe_det):
        """check for multiple fish intersecting with the pipe and adjust hit counter accordingly"""
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.check_for_hit")
        if (len(fish_dets) < 2) or (len(pipe_det) != 1):
            self.hit_counter.decrement()
            return False
        intersect_count = 0
        pipe_det = pipe_det[0]
        for det in fish_dets:
            intersect = detect.BBox.intersect(det.bbox, pipe_det.bbox)
            intersect_count += intersect.valid
        if intersect_count < 2:
            self.hit_counter.decrement()
            self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.check_for_hit")
            return False
        else:
            self.hit_counter.increment()
            self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.check_for_hit")
            return True

    def filter_dets(self, dets):
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.filter_dets")
        fish_dets = [d for d in dets if d.id == self.ids['fish']][:self.MAX_FISH]
        pipe_det = [d for d in dets if d.id == self.ids['pipe']][:1]
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.filter_dets")
        return fish_dets, pipe_det

    def notify(self):
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.notify")
        # TODO: write notification function
        pass
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.notify")

    def shutdown(self):
        self.logger.log(logging.DEBUG, f"Entering DetectorWorker.shutdown")
        [self.overlay_boxes(be) for be in self.buffer]
        self.logger.log(logging.INFO, f'average time for detection loop: {self.avg_timer.avg * 1000}ms')
        self.img_q.safe_close()
        self.logger.log(logging.DEBUG, f"Exiting DetectorWorker.shutdown")



