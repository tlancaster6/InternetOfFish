from internet_of_fish.modules.mptools import QueueProcWorker

class NotifierWorker(QueueProcWorker):

    def startup(self):
        pass

    def init_args(self, args):
        self.notification_q, = args

    def main_func(self):
        pass

    def shutdown(self):
        self.notification_q.close()
        self.event_q.close()

