import sys
from typing import Tuple

from internet_of_fish.modules import mptools, collector, detector, utils, uploader, notifier
import time
import datetime as dt


class RunnerWorker(mptools.ProcWorker):

    def init_args(self, args: Tuple[mptools.MainContext,]):
        self.logger.debug(f"Entering RunnerWorker.init_args : {args}")
        self.main_ctx, = args
        self.logger.debug(f"Exiting RunnerWorker.init_args")

    def startup(self):
        self.logger.debug(f"Entering RunnerWorker.startup")
        self.die_time = dt.datetime.fromisoformat('T'.join([self.metadata['end_date'], self.metadata['end_time']]))
        self.logger.debug(f"RunnerWorker.die_time set to {self.die_time}")
        self.curr_mode = self.expected_mode()
        self.logger.debug(f'RunnerWorker.curr_mode initialized as {self.curr_mode}')
        self.event_q.safe_put(mptools.EventMessage(self.name, f'ENTER_{self.curr_mode.upper()}_MODE', 'kickstart'))
        self.logger.debug(f'kickstarting RunnerWorker with ENTER_{self.curr_mode.upper()}_MODE')
        self.logger.debug(f"Exiting RunnerWorker.startup")

    def main_func(self):
        self.logger.debug(f"Entering RunnerWorker.main_func")
        if dt.datetime.now() > self.die_time:
            self.logger.info(f"RunnerWorker injected a HARD_SHUTDOWN into the event queue")
            self.event_q.safe_put(mptools.EventMessage(self.name, 'HARD_SHUTDOWN', 'die_time exceeded'))

        event = self.event_q.safe_get()
        if not event:
            self.verify_mode()
        elif event.msg_type in ['FATAL', 'HARD_SHUTDOWN']:
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Executing hard shutdown')
            self.shutdown()
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
        self.soft_shutdown()
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
                time.sleep(utils.sleep_until_morning())

    def expected_mode(self):
        if self.metadata['source']:
            return self.curr_mode if self.curr_mode else 'active'
        elif utils.lights_on():
            return 'active'
        else:
            return 'passive'

    def active_mode(self):
        self.curr_mode = 'active'
        img_q = self.main_ctx.MPQueue()
        notification_q = self.main_ctx.MPQueue()
        if self.metadata['source'] != 'None':
            self.main_ctx.Proc('COLLECT', collector.VideoCollectorWorker, img_q, self.metadata['source'])
        else:
            self.main_ctx.Proc('COLLECT', collector.CollectorWorker, img_q)
        self.main_ctx.Proc('DETECT', detector.DetectorWorker, img_q, notification_q)
        self.main_ctx.Proc('NOTIFY', notifier.NotifierWorker, notification_q)

    def passive_mode(self):
        self.curr_mode = 'passive'
        time.sleep(10)
        notification_q = self.main_ctx.MPQueue()
        self.main_ctx.Proc('UPLOAD', uploader.UploaderWorker)
        self.main_ctx.Proc('NOTIFY', notifier.NotifierWorker, notification_q)

    def hard_shutdown(self):
        for _ in range(3):
            self.main_ctx.stop_procs()
            self.main_ctx.stop_queues()
            if (not self.main_ctx.procs) and (not self.main_ctx.queues):
                break
        sys.exit()

    def soft_shutdown(self):
        time.sleep(1)
        self.logger.debug(f'entering soft_shutdown. Terminating {len(self.main_ctx.procs)} processes and '
                          f'{len(self.main_ctx.queues)} queues')
        num_failed, num_terminated = self.main_ctx.stop_procs(kill_all=False)
        num_items_left = self.main_ctx.stop_queues()
        self.logger.debug(f'exiting soft_shutdown. {num_terminated} processes successfully terminated. {num_items_left}'
                          f'items drained from queues.')
        if num_failed:
            self.logger.warning(f'during a soft shutdown, {num_failed} failed to terminate')







