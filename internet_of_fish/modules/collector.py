import logging, os, io, time
from PIL import Image
from internet_of_fish.modules import mptools
from internet_of_fish.modules.utils import gen_utils
import picamera
import cv2
import datetime as dt


class CollectorWorker(mptools.TimerProcWorker, metaclass=gen_utils.AutologMetaclass):


    def init_args(self, args):
        self.img_q, = args
        self.INTERVAL_SECS = self.defs.INTERVAL_SECS
        self.RESOLUTION = (self.defs.H_RESOLUTION, self.defs.V_RESOLUTION)  # pi camera resolution
        self.FRAMERATE = self.defs.FRAMERATE  # pi camera framerate
        self.SPLIT_AM_PM = self.defs.SPLIT_AM_PM

    def startup(self):
        self.cam = self.init_camera()
        self.vid_dir = self.defs.PROJ_VID_DIR
        self.cam.start_recording(self.generate_vid_path())
        self.split_flag = False if dt.datetime.now().hour < 12 else True

    def main_func(self):
        cap_time = gen_utils.current_time_ms()
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', use_video_port=True)
        stream.seek(0)
        img = Image.open(stream)
        img.load()
        put_result = self.img_q.safe_put((cap_time, img))
        stream.close()
        if not put_result:
            self.INTERVAL_SECS += 0.1
            self.logger.info(f'img_q full, slowing collection interval to {self.INTERVAL_SECS}')
        if self.SPLIT_AM_PM and (dt.datetime.now().hour > 12) and not self.split_flag:
            self.split_recording()
            self.split_flag = True

    def shutdown(self):
        self.cam.stop_recording()
        self.cam.close()
        self.img_q.safe_put('END')
        self.img_q.close()
        self.event_q.close()

    def init_camera(self):
        cam = picamera.PiCamera()
        cam.resolution = self.RESOLUTION
        cam.framerate = self.FRAMERATE
        return cam

    def generate_vid_path(self):
        return os.path.join(self.vid_dir, f'{gen_utils.current_time_iso()}.h264')

    def split_recording(self):
        self.cam.split_recording(self.generate_vid_path())


class SourceCollectorWorker(CollectorWorker):

    """functions like a CollectorWorker, but gathers images from an existing file rather than a camera"""

    def init_args(self, args):
        self.img_q, self.video_file = args
        self.VIRTUAL_INTERVAL_SECS = self.defs.INTERVAL_SECS
        self.INTERVAL_SECS = 0.1

    def startup(self):
        if not os.path.exists(self.video_file):
            self.locate_video()
        self.cam = cv2.VideoCapture(self.video_file)
        self.cap_rate = max(1, int(self.cam.get(cv2.CAP_PROP_FPS) * self.VIRTUAL_INTERVAL_SECS))
        self.logger.log(logging.INFO, f"Collector will add an image to the queue every {self.cap_rate} frame(s)")
        self.frame_count = 0
        self.active = True

    def main_func(self):
        if not self.active:
            time.sleep(1)
            return
        cap_time = gen_utils.current_time_ms()
        ret, frame = self.cam.read()
        if ret:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            put_result = self.img_q.safe_put((cap_time, img))
            while not put_result:
                self.INTERVAL_SECS += 0.1
                self.logger.debug(f'img_q full, increasing loop interval to {self.INTERVAL_SECS}')
                time.sleep(self.INTERVAL_SECS)
                put_result = self.img_q.safe_put((cap_time, img))
            self.frame_count += self.cap_rate
            self.cam.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)
        else:
            self.active = False
            self.logger.log(logging.INFO, "VideoCollector entering sleep mode (no more frames to process)")
            self.img_q.safe_put('END')

    def locate_video(self):
        path_elements = [self.defs.HOME_DIR,
                         * os.path.relpath(self.defs.DATA_DIR, self.defs.HOME_DIR).split(os.sep),
                         self.metadata['proj_id'],
                         'Videos']
        for i in range(len(path_elements)):
            potential_path = os.path.join(*path_elements[:i+1], self.video_file)
            self.logger.debug(f'checking for video in {potential_path}')
            if os.path.exists(potential_path):
                self.video_file = potential_path
                break
            self.logger.debug('no video found')
        if not os.path.exists(self.video_file):
            self.logger.log(logging.ERROR, f'failed to locate video file {self.video_file}. '
                                           f'Try placing it in {self.defs.HOME_DIR}')
            raise FileNotFoundError


    def shutdown(self):
        self.img_q.close()
        self.event_q.close()


class SimpleCollectorWorker(CollectorWorker):
    # TODO: write a collector worker that doesn't collect images, just video
    pass

class DepthCollectorWorker(CollectorWorker):
    # TODO: write a collector worker that collects video and depth (but not images)
    pass
