from internet_of_fish.modules.mptools import QueueProcWorker
from internet_of_fish.modules.definitions import PROJ_DIR
from internet_of_fish.modules.utils.gen_utils import recursive_mtime
import psutil
import datetime as dt


class StatusReport:

    def __init__(self, proj_id, curr_mode, curr_procs, last_event):
        """
        Simple container class for standardizing and partially automating the status reports that pass between the
        clients and server. Instances of the StatusReport class can be called without arguments to return the instance
        attributes in dictionary form (see Runner.status_report method for a usage example)

        :param proj_id: project id for the currently running project
        :type proj_id: str
        :param curr_mode: the mode (either 'active' or 'passive') of the Runner process
        :type curr_mode: str
        :param curr_procs: list of names of the processes that are currently alive in the main context
        :type curr_procs: list[str]
        :param last_event: msg_type attribute of the most recent mptools.EventMessage object received and processed by
            the runner process (e.g., 'HARD_SHUTDOWN', 'ENTER_ACTIVE_MODE', etc.)
        :type last_event: str
        """
        # store the provided arguments as attributes
        self.proj_id = proj_id
        self.curr_mode = curr_mode
        self.curr_procs = curr_procs
        self.last_event = last_event
        # generate additional attributes programmatically
        self.disk_usage = float(psutil.disk_usage('/').percent)
        self.mem_usage = float(psutil.virtual_memory().percent)
        self.idle_time = (dt.datetime.now() - recursive_mtime(PROJ_DIR(proj_id))).total_seconds()

    def __call__(self):
        return {key: str(val) for key, val in vars(self).items()}


class WatcherWorker(QueueProcWorker):

    def startup(self):
        """This function gets called once, during the class initialization. Any code you would put in __init__ can go
        here, without overriding the boilerplate code from the QueueProcWorker parent class.
        """
        self.last_report = None
        # TODO: Probably set up some of the socket stuff here?

    def main_func(self, item):
        """
        this function executes every time the Runner adds a new status report dictionary (of the type returned by
        StatusReport.call) to the status queue, and sends that dictionary to the server.
        :param item: dictionary of pertinent status readings, of the form returned by StatusReport.call
        :type item: dict
        """
        # set the "last_report" attribute to the new report. This attribute doesn't have a use yet, but can be used to
        # check for changes in status that might trigger different behavior
        self.last_report = item
        # TODO: Connect to the server (if necessary?) and send the status report here


