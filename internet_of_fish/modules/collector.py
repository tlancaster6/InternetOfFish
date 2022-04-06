import logging, os, io, time
from PIL import Image
from internet_of_fish.modules import mptools
from internet_of_fish.modules import utils
from internet_of_fish.modules import definitions
import picamera
import cv2


class CollectorWorker(mptools.TimerProcWorker, metaclass=utils.AutologMetaclass):
    INTERVAL_SECS = definitions.INTERVAL_SECS
    RESOLUTION = definitions.RESOLUTION  # pi camera resolution
    FRAMERATE = definitions.FRAMERATE  # pi camera framerate
    DATA_DIR = definitions.DATA_DIR
    MAX_VIDEO_LEN = definitions.MAX_VIDEO_LEN

    def init_args(self, args):
        self.img_q, = args

    def startup(self):
        self.cam = self.init_camera()
        self.vid_dir =definitions.PROJ_VID_DIR(self.metadata['proj_id'])
        self.cam.start_recording(self.generate_vid_path())
        self.last_split = time.time()

    def main_func(self):
        cap_time = utils.current_time_ms()
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
        if (time.time() - self.last_split) > self.MAX_VIDEO_LEN:
            self.split_recording()

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
        return os.path.join(self.vid_dir, f'{utils.current_time_iso()}.h264')

    def split_recording(self):
        self.cam.split_recording(self.generate_vid_path())
        self.last_split = time.time()


class VideoCollectorWorker(CollectorWorker):
    VIRTUAL_INTERVAL_SECS = definitions.INTERVAL_SECS
    INTERVAL_SECS = 0.1
    """functions like a CollectorWorker, but gathers images from an existing file rather than a camera"""

    def init_args(self, args):
        self.img_q, self.video_file = args
        self.video_file.replace(':', '\:')

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
        cap_time = utils.current_time_ms()
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
        path_elements = [definitions.HOME_DIR,
                         * os.path.relpath(self.DATA_DIR, definitions.HOME_DIR).split(os.sep),
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
                                           f'Try placing it in {definitions.HOME_DIR}')
            raise FileNotFoundError


    def shutdown(self):
        self.img_q.close()
        self.event_q.close()
