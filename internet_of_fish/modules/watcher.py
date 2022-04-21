from internet_of_fish.modules.mptools import QueueProcWorker

class WatcherWorker(QueueProcWorker):

    def main_func(self, item):
        # TODO: write a function that accepts the output of runner.status_report() as item and sends a status report to the controller
        pass


