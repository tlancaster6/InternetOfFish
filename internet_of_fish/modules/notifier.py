from internet_of_fish.modules import mptools, utils


class Notification:
    def __init__(self, msg_src, msg_type, msg, attachment_path):
        self.msg_src, self.msg_type, self.msg, self.attachment_path = msg_src, msg_type, msg, attachment_path
        self.id = utils.current_time_iso()

    def __str__(self):
        return (f"time: {self.id}\n"
                f"source: {self.msg_src}\n"
                f"type: {self.msg_type}\n"
                f"message: {self.msg}\n"
                f"attachment: {self.attachment_path}")


class NotifierWorker(mptools.QueueProcWorker):

    def startup(self):
        self.user_email = self.metadata['email']

    def main_func(self, notification):
        self.logger.info(f'notification sent to user:\n{notification}')

    def shutdown(self):
        self.work_q.close()
        self.event_q.close()

