from internet_of_fish.modules.mptools import QueueProcWorker
from internet_of_fish.modules.definitions import PROJ_DIR
from internet_of_fish.modules.utils.gen_utils import recursive_mtime
import psutil
import datetime as dt


class StatusReport:

    def __init__(self, proj_id, curr_mode, curr_procs, last_event):
        self.disk_usage = float(psutil.disk_usage('/').percent)
        self.mem_usage = float(psutil.virtual_memory().percent)
        self.curr_mode = curr_mode
        self.curr_procs = curr_procs
        self.last_event = last_event
        self.idle_time = dt.datetime.now() - recursive_mtime(PROJ_DIR(proj_id)).total_seconds()

    def __call__(self):
        return {key: str(val) for key, val in vars(self).items()}


class WatcherWorker(QueueProcWorker):

    def startup(self):
        self.last_report = None

    def main_func(self, item):
        pass


