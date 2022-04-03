import logging, os, io, time
from PIL import Image
from internet_of_fish.modules import mptools
from internet_of_fish.modules import utils
from internet_of_fish.modules import definitions
import picamera
import cv2


class CollectorWorker(mptools.TimerProcWorker):
    INTERVAL_SECS = definitions.INTERVAL_SECS
    RESOLUTION = definitions.RESOLUTION  # pi camera resolution
    FRAMERATE = definitions.FRAMERATE  # pi camera framerate
    DATA_DIR = definitions.DATA_DIR
    MAX_VIDEO_LEN = definitions.MAX_VIDEO_LEN

    def init_args(self, args):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.init_args : {args}")
        self.img_q, = args
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.init_args")

    def startup(self):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.startup")
        self.cam = self.init_camera()
        self.vid_dir =definitions.PROJ_VID_DIR(self.metadata['proj_id'])
        self.cam.start_recording(self.generate_vid_path())
        self.last_split = time.time()
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.startup")

    def main_func(self):
        cap_time = utils.current_time_ms()
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.main_func")
        stream = io.BytesIO()
        self.cam.capture(stream, format='jpeg', use_video_port=True)
        stream.seek(0)
        img = Image.open(stream)
        img.load()
        self.img_q.safe_put((cap_time, img))
        stream.close()
        if (time.time() - self.last_split) > self.MAX_VIDEO_LEN:
            self.split_recording()
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.main_func")

    def shutdown(self):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.shutdown")
        self.cam.stop_recording()
        self.cam.close()
        self.img_q.safe_put('END')
        self.img_q.close()
        self.event_q.close()
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.shutdown")

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
    INTERVAL_SECS = 0.02
    """functions like a CollectorWorker, but gathers images from an existing file rather than a camera"""

    def init_args(self, args):
        self.logger.log(logging.DEBUG, f"Entering VideoCollectorWorker.init_args : {args}")
        self.img_q, self.video_file = args
        self.logger.log(logging.DEBUG, f"Exiting VideoCollectorWorker.init_args")

    def startup(self):
        self.logger.log(logging.DEBUG, f"Entering VideoCollectorWorker.startup")
        if not os.path.exists(self.video_file):
            self.locate_video()
        self.cam = cv2.VideoCapture(self.video_file)
        self.cap_rate = max(1, int(self.cam.get(cv2.CAP_PROP_FPS) * self.VIRTUAL_INTERVAL_SECS))
        self.logger.log(logging.INFO, f"Collector will add an image to the queue every {self.cap_rate} frame(s)")
        self.frame_count = 0
        self.active = True
        self.logger.log(logging.DEBUG, f"Exiting VideoCollectorWorker.startup")

    def main_func(self):
        if not self.active:
            time.sleep(1)
            return
        self.logger.log(logging.DEBUG, f"Entering VideoCollectorWorker.main_func")
        cap_time = utils.current_time_ms()
        ret, frame = self.cam.read()
        if ret:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.img_q.safe_put((cap_time, img))
            self.frame_count += self.cap_rate
            self.cam.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)
        else:
            self.active = False
            self.logger.log(logging.INFO, "VideoCollector entering sleep mode (no more frames to process)")
            self.img_q.safe_put('SOFT_SHUTDOWN')
        self.logger.log(logging.DEBUG, f"Exiting VideoCollectorWorker.main_func")

    def locate_video(self):
        self.logger.log(logging.DEBUG, f"Entering VideoCollectorWorker.locate_video")
        path_elements = [definitions.HOME_DIR,
                         * os.path.relpath(self.DATA_DIR, definitions.HOME_DIR).split(os.sep),
                         self.metadata['proj_id'],
                         'Videos']
        for i in range(len(path_elements)):
            potential_path = os.path.join(*path_elements[:i], self.video_file)
            if os.path.exists(potential_path):
                self.video_file = potential_path
                break
        if not os.path.exists(self.video_file):
            self.logger.log(logging.ERROR, f'failed to locate video file {self.video_file}. '
                                           f'Try placing it in {definitions.HOME_DIR}')
            raise FileNotFoundError
        self.logger.log(logging.DEBUG, f"Exiting VideoCollectorWorker.locate_video")


    def shutdown(self):
        self.logger.log(logging.DEBUG, f"Entering VideoCollectorWorker.shutdown")
        self.cam.release()
        self.img_q.close()
        self.event_q.close()
        self.logger.log(logging.DEBUG, f"Exiting VideoCollectorWorker.shutdown")
