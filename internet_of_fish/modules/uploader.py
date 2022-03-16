from internet_of_fish.modules.mptools import QueueProcWorker

class UploaderWorker(QueueProcWorker):
    #TODO: write the upload worker class

    def init_args(self, args):
        self.upload_q, = args
