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


class DetectorWorker(mptools.QueueProcWorker, metaclass=utils.AutologMetaclass):
    MODELS_DIR = definitions.MODELS_DIR
    DATA_DIR = definitions.DATA_DIR
    HIT_THRESH = definitions.HIT_THRESH
    IMG_BUFFER = definitions.IMG_BUFFER

    def init_args(self, args):
        self.work_q, = args

    def startup(self):
        self.max_fish = definitions.MAX_FISH if self.metadata['n_fish'] == 'None' else int(self.metadata['max_fish'])
        self.img_dir = definitions.PROJ_IMG_DIR(self.metadata['proj_id'])

        model_path = glob(os.path.join(self.MODELS_DIR, self.metadata['model_id'], '*.tflite'))[0]
        label_path = glob(os.path.join(self.MODELS_DIR, self.metadata['model_id'], '*.txt'))[0]
        self.interpreter = make_interpreter(model_path)
        self.interpreter.allocate_tensors()

        self.labels = read_label_file(label_path)
        self.ids = {val: key for key, val in self.labels.items()}

        self.hit_counter = HitCounter()
        self.avg_timer = utils.Averager()
        self.buffer = []
        self.loop_counter = 1

    def main_func(self, q_item):
        cap_time, img = q_item
        dets = self.detect(img)
        fish_dets, pipe_det = self.filter_dets(dets)
        self.buffer.append(BufferEntry(cap_time, img, fish_dets + pipe_det))
        self.check_for_hit(fish_dets, pipe_det)
        if self.hit_counter.hits >= self.HIT_THRESH:
            self.logger.log(logging.INFO, f"Hit threshold of {self.HIT_THRESH} exceeded, possible spawning event")
            img_paths = [self.overlay_boxes(be) for be in self.buffer]
            vid_path = self.jpgs_to_mp4(img_paths)
            msg = f'possible spawning event in {self.metadata["tank_id"]} at {utils.current_time_iso()}'
            self.event_q.safe_put(('SPAWNING_EVENT', msg, vid_path))
            self.hit_counter.reset()
            self.buffer = []
        if len(self.buffer) > self.IMG_BUFFER:
            self.buffer.pop(0)
        self.print_info()

    def print_info(self):
        if not self.loop_counter % 100:
            self.logger.info(f'{self.loop_counter} detection loops completed. current average detection time is '
                             f'{self.avg_timer.avg * 1000}ms')

    def detect(self, img):
        """run detection on a single image"""
        start = time.time()
        _, scale = common.set_resized_input(
            self.interpreter, img.size, lambda size: img.resize(size, Image.ANTIALIAS))
        self.interpreter.invoke()
        dets = detect.get_objects(self.interpreter, definitions.CONF_THRESH, scale)
        self.avg_timer.update(time.time() - start)
        return dets

    def overlay_boxes(self, buffer_entry: BufferEntry):
        """open an image, draw detection boxes, and replace the original image"""
        draw = ImageDraw.Draw(buffer_entry.img)
        for det in buffer_entry.dets:
            bbox = det.bbox
            draw.rectangle([(bbox.xmin, bbox.ymin), (bbox.xmax, bbox.ymax)],
                           outline='red')
            draw.text((bbox.xmin + 10, bbox.ymin + 10),
                      '%s\n%.2f' % (self.labels.get(det.id, det.id), det.score),
                      fill='red')
        img_path = os.path.join(self.img_dir, f'{buffer_entry.cap_time}.jpg')
        buffer_entry.img.save(img_path)
        return img_path

    def jpgs_to_mp4(self, img_paths, delete_jpgs=True):
        """convert a series of jpgs to a single mp4, and (if delete_jpgs) delete the original images"""
        dest_dir = definitions.PROJ_VID_DIR(self.metadata['proj_id'])
        vid_path = utils.jpgs_to_mp4(img_paths, dest_dir)
        if delete_jpgs:
            [os.remove(x) for x in img_paths]
        return vid_path

    def check_for_hit(self, fish_dets, pipe_det):
        """check for multiple fish intersecting with the pipe and adjust hit counter accordingly"""
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
            return False
        else:
            self.hit_counter.increment()
            return True

    def filter_dets(self, dets):
        """keep only the the highest confidence pipe detection, and the top n highest confidence fish detections"""
        fish_dets = [d for d in dets if d.id == self.ids['fish']][:self.max_fish]
        pipe_det = [d for d in dets if d.id == self.ids['pipe']][:1]
        return fish_dets, pipe_det

    def shutdown(self):
        if self.avg_timer.avg:
            self.logger.log(logging.INFO, f'average time for detection loop: {self.avg_timer.avg * 1000}ms')
        self.work_q.close()
        self.event_q.close()



