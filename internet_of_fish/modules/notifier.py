from internet_of_fish.modules import mptools
from internet_of_fish.modules.utils import gen_utils
import base64
import os
from datetime import datetime as dt
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName,
    FileType, Disposition)

class Notification:
    def __init__(self, msg_src, msg_type, msg, attachment_path):
        self.msg_src, self.msg_type, self.msg, self.attachment_path = msg_src, msg_type, msg, attachment_path
        self.id = gen_utils.current_time_iso()

    def __str__(self):
        return (f"time: {self.id}\n"
                f"source: {self.msg_src}\n"
                f"type: {self.msg_type}\n"
                f"message: {self.msg}\n"
                f"attachment: {self.attachment_path}")

    def timestamp(self):
        return dt.fromisoformat(self.id).timestamp()


class NotifierWorker(mptools.QueueProcWorker, metaclass=gen_utils.AutologMetaclass):

    def startup(self):
        self.MIN_NOTIFICATION_INTERVAL = self.defs.MIN_NOTIFICATION_INTERVAL
        self.user_email = self.metadata['email']
        with open(self.defs.SENDGRID_KEY_FILE, 'r') as f:
            api_key = f.read().strip()
        self.api_client = SendGridAPIClient(api_key)
        self.last_notification = None

    def main_func(self, notification: Notification):
        if not self.check_notification_conditions(notification):
            self.logger.debug('one or more notification conditions unmet. Aborting notification')
            return

        self.logger.info(f'sending notification to user:\n{notification}')
        tries_left = self.defs.MAX_TRIES
        while tries_left:
            tries_left -= 1
            try:
                message = self.notification_to_sendgrid_message(notification)
                response = self.api_client.send(message)
                if str(response.status_code) == '202':
                    self.logger.debug('notification appears to have sent successfully')
                    break
                else:
                    self.logger.debug(f'expected response status code of 202, got {response.status_code}. retrying')
            except Exception as e:
                self.logger.debug(f'failed to send message. {tries_left} tries remaining')
                print(e)

    def check_notification_conditions(self, notification: Notification):
        if not self.last_notification:
            return True
        if self.last_notification.msg_type != notification.msg_type:
            return True
        if (notification.timestamp() - self.last_notification.timestamp()) > self.MIN_NOTIFICATION_INTERVAL:
            return True
        return False

    def notification_to_sendgrid_message(self, notification: Notification):
        message = Mail(
            from_email='themcgrathlab@gmail.com',
            to_emails=self.user_email,
            subject=notification.msg_type,
            html_content=notification.msg)
        with open(notification.attachment_path, 'rb') as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        attachment = Attachment()
        attachment.file_content = FileContent(encoded)
        attachment.file_type = FileType('application/mp4')
        attachment.file_name = FileName(os.path.basename(notification.attachment_path))
        attachment.disposition = Disposition('attachment')
        message.attachment = attachment
        return message


    def shutdown(self):
        self.work_q.close()
        self.event_q.close()

