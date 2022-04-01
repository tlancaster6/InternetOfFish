from typing import Tuple
from internet_of_fish.modules import mptools, collector, detector, utils, uploader, notifier
import time
import datetime as dt
from unittest.mock import patch


class RunnerWorker(mptools.ProcWorker):

    def init_args(self, args: Tuple[mptools.MainContext,]):
        self.logger.debug(f"Entering RunnerWorker.init_args : {args}")
        self.main_ctx, = args
        self.curr_mode = self.expected_mode()
        self.logger.debug(f'RunnerWorker.curr_mode initialized as {self.curr_mode}')
        self.logger.debug(f"Exiting RunnerWorker.init_args")

    def startup(self):
        self.logger.debug(f"Entering RunnerWorker.startup")
        self.secondary_ctx = None
        self.collect_proc, self.detect_proc, self.upload_proc, self.notify_proc = None, None, None, None
        self.img_q, self.notification_q = None, None
        self.die_time = dt.datetime.fromisoformat('T'.join([self.metadata['end_date'], self.metadata['end_time']]))
        self.logger.debug(f"RunnerWorker.die_time set to {self.die_time}")
        self.event_q.safe_put(mptools.EventMessage(self.name, f'ENTER_{self.curr_mode.upper()}_MODE', 'kickstart'))
        self.logger.debug(f'kickstarting RunnerWorker with ENTER_{self.curr_mode.upper()}_MODE')
        self.logger.debug(f"Exiting RunnerWorker.startup")


    def main_func(self):
        self.logger.debug(f"Entering RunnerWorker.main_func")
        if dt.datetime.now() > self.die_time:
            self.logger.info(f"RunnerWorker injected a HARD_SHUTDOWN into the event queue")
            self.event_q.safe_put(mptools.EventMessage(self.name, 'HARD_SHUTDOWN', 'die_time exceeded'))

        event = self.event_q.safe_get()
        if event:
            self.logger.debug(f'Runner received event: {event}')
        if not event:
            self.verify_mode()
        elif event.msg_type in ['FATAL', 'HARD_SHUTDOWN']:
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Executing hard shutdown')
            self.hard_shutdown()
        elif event.msg_type == 'SOFT_SHUTDOWN':
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Executing soft shutdown')
            self.soft_shutdown()
        elif event.msg_type == 'ENTER_ACTIVE_MODE':
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Switching to active mode')
            self.active_mode()
        elif event.msg_type == 'ENTER_PASSIVE_MODE':
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Switching to passive mode in 10 seconds')
            self.passive_mode()
        else:
            self.logger.error(f"Unknown Event: {event}")
        self.logger.debug(f"exiting RunnerWorker.main_func")

    def shutdown(self):
        self.hard_shutdown()

    def verify_mode(self):
        if self.curr_mode == 'active':
            if self.expected_mode() == 'passive':
                self.event_q.safe_put(mptools.EventMessage(self.name, 'SOFT_SHUTDOWN', 'mode switch'))
                self.event_q.safe_put(mptools.EventMessage(self.name, 'ENTER_PASSIVE_MODE', 'mode switch'))
            else:
                time.sleep(0.1)
        elif self.curr_mode == 'passive':
            if self.expected_mode() == 'active':
                self.event_q.safe_put(mptools.EventMessage(self.name, 'SOFT_SHUTDOWN', 'mode switch'))
                self.event_q.safe_put(mptools.EventMessage(self.name, 'ENTER_ACTIVE_MODE', 'mode switch'))
            else:
                sleep_time = utils.sleep_until_morning()
                self.logger.debug(f'no change in mode. going back to sleep for {sleep_time} seconds')
                time.sleep(sleep_time)

    def expected_mode(self):
        if self.metadata['source'] != 'None':
            try:
                return self.curr_mode
            except AttributeError:
                return 'active'
        elif utils.lights_on():
            return 'active'
        else:
            return 'passive'

    def active_mode(self):
        self.secondary_ctx = mptools.SecondaryContext(self.main_ctx.metadata, self.event_q)
        self.curr_mode = 'active'
        self.img_q = self.secondary_ctx.MPQueue()
        self.notification_q = self.secondary_ctx.MPQueue()
        if self.metadata['source'] != 'None':
            self.collect_proc = self.secondary_ctx.Proc(
                'COLLECT', collector.VideoCollectorWorker, self.img_q, self.metadata['source'])
        else:
            self.collect_proc = self.secondary_ctx.Proc(
                'COLLECT', collector.CollectorWorker, self.img_q)
        self.detect_proc = self.secondary_ctx.Proc(
            'DETECT', detector.DetectorWorker, self.img_q)
        self.notify_proc = self.secondary_ctx.Proc('NOTIFY', notifier.NotifierWorker, self.notification_q)

    def passive_mode(self):
        self.secondary_ctx = mptools.SecondaryContext(self.main_ctx.metadata, self.event_q)
        self.curr_mode = 'passive'
        time.sleep(10)
        self.notification_q = self.secondary_ctx.MPQueue()
        self.upload_proc = self.secondary_ctx.Proc('UPLOAD', uploader.UploaderWorker)
        self.notify_proc = self.secondary_ctx.Proc('NOTIFY', notifier.NotifierWorker, self.notification_q)

    def hard_shutdown(self):
        time.sleep(1)
        self.soft_shutdown()
        self.logger.debug(f'entering hard_shutdown.')
        self.main_ctx.stop_procs()
        self.main_ctx.stop_queues()
        self.logger.debug(f'exiting hard shutdown.')
        self.logger.info(f'Program exiting')

    def soft_shutdown(self):
        time.sleep(1)
        self.logger.debug(f'entering soft_shutdown')
        if not self.secondary_ctx:
            self.logger.debug('secondary context has already been shut down')
            return
        self.secondary_ctx.stop_procs()
        self.secondary_ctx.stop_queues()
        self.secondary_ctx = None
        self.logger.debug('exiting soft_shutdown.')


class TestingRunnerWorker(RunnerWorker):

    def init_args(self, args: Tuple[mptools.MainContext,]):
        self.logger.debug(f"Entering RunnerWorker.init_args : {args}")
        self.main_ctx, = args
        self.curr_mode = 'active'
        patch('collector.utils.lights_on', new_callable=lambda _: True if self.curr_mode == 'active' else False)
        self.logger.debug(f"Exiting RunnerWorker.init_args")

    def expected_mode(self):

        mode_map = {'active': 'passive', 'passive': 'active'}
        if not dt.datetime.now().minute % 3:
            return mode_map[self.curr_mode]
        else:
            return self.curr_mode









