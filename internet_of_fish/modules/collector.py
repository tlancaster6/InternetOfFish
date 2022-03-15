import logging, picamera, os, io
from PIL import Image
from internet_of_fish.modules import mptools
from internet_of_fish.modules import utils
from internet_of_fish.modules import definitions


class CollectorWorker(mptools.TimerProcWorker):
    INTERVAL_SECS = 1
    RESOLUTION = (1296, 972)  # pi camera resolution
    FRAMERATE = 30  # pi camera framerate
    DATA_DIR = definitions.DATA_DIR

    def init_args(self, args):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.init_args : {args}")
        self.img_q, = args
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.init_args")

    def startup(self):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.startup")
        self.cam = picamera.PiCamera()
        self.cam.resolution = self.RESOLUTION
        self.cam.framerate = self.FRAMERATE
        vid_dir = os.path.join(self.DATA_DIR, self.params.proj_id, 'Videos')
        os.makedirs(vid_dir, exist_ok=True)
        self.cam.start_recording(os.path.join(vid_dir, f'{utils.current_time_iso()}.h264'))
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.startup")

    def main_func(self):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.main_func")
        stream = io.BytesIO()
        cap_time = utils.current_time_ms()
        self.cam.capture(stream, format='jpeg', use_video_port=True)
        stream.seek(0)
        img = Image.open(stream)
        img.load()
        self.img_q.safe_put((cap_time, img))
        stream.close()
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.main_func")

    def shutdown(self):
        self.logger.log(logging.DEBUG, f"Entering CollectorWorker.shutdown")
        self.cam.stop_recording()
        self.cam.close()
        self.img_q.safe_close()
        self.logger.log(logging.DEBUG, f"Exiting CollectorWorker.shutdown")
