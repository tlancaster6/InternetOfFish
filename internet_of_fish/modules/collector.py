import logging, picamera, os, io
from pycoral.adapters import common, detect
from pycoral.utils.dataset import read_label_file
from pycoral.utils.edgetpu import make_interpreter
from PIL import Image
from internet_of_fish.modules.workers import TimerProcWorker
from internet_of_fish.modules.utils import _current_time_ms, _current_time_iso


class CollectorWorker(TimerProcWorker):
    INTERVAL_SECS = 1
    RESOLUTION = (1296, 972)  # pi camera resolution
    FRAMERATE = 30  # pi camera framerate

    def init_args(self, args):
        self.log(logging.DEBUG, f"Entering CollectorWorker.init_args : {args}")
        self.img_q, self.proj_id = args

    def startup(self):
        self.cam = picamera.PiCamera()
        self.cam.resolution = self.RESOLUTION
        self.cam.framerate = self.FRAMERATE
        vid_dir = os.path.join(self.DATA_DIR, self.proj_id, 'Videos')
        os.makedirs(vid_dir, exist_ok=True)
        self.cam.start_recording(os.path.join(vid_dir, f'{_current_time_iso()}.h264'))

    def main_func(self):
        stream = io.BytesIO()
        cap_time = _current_time_ms()
        self.cam.capture(stream, format='jpeg', use_video_port=True)
        stream.seek(0)
        img = Image.open(stream)
        img.load()
        self.img_q.safe_put((cap_time, img))
        stream.close()

    def shutdown(self):
        self.cam.close()
