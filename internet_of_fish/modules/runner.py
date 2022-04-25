from typing import Tuple

from internet_of_fish.modules.utils import file_utils
from internet_of_fish.modules import mptools
from internet_of_fish.modules import collector
from internet_of_fish.modules import detector
from internet_of_fish.modules.utils import gen_utils
from internet_of_fish.modules import uploader
from internet_of_fish.modules import notifier
from internet_of_fish.modules import definitions
# from internet_of_fish.modules import watcher
import time
import datetime as dt
import os
import glob
import subprocess as sp
import shutil
import pathlib

EVENT_TYPES = ['NOTIFY', 'FATAL', 'HARD_SHUTDOWN', 'SOFT_SHUTDOWN', 'ENTER_ACTIVE_MODE', 'ENTER_PASSIVE_MODE',
               'ENTER_END_MODE', 'MOCK_HIT']

class RunnerWorker(mptools.ProcWorker, metaclass=gen_utils.AutologMetaclass):

    def init_args(self, args: Tuple[mptools.MainContext,]):
        self.main_ctx, = args
        self.curr_mode = self.expected_mode()
        self.logger.debug(f'RunnerWorker.curr_mode initialized as {self.curr_mode}')

    def startup(self):
        self.event_types = EVENT_TYPES
        self.MAX_UPLOAD_WORKERS = self.defs.MAX_UPLOAD_WORKERS
        # self.STATUS_INTERVAL = self.defs.STATUS_INTERVAL
        # self.status_report_deadline = time.time() + self.STATUS_INTERVAL
        self.last_event = None

        self.main_ctx.Proc('NOTIFY', notifier.NotifierWorker, self.main_ctx.notification_q)
        # self.status_queue = self.main_ctx.MPQueue(maxsize=10)
        # self.main_ctx.Proc('WATCH', watcher.WatcherWorker, self.status_queue)
        self.secondary_ctx = None

        self.die_time = dt.datetime.combine(self.metadata['end_date'], self.metadata['end_time'])
        self.logger.debug(f"RunnerWorker.die_time set to {self.die_time}")

        self.event_q.safe_put(mptools.EventMessage(self.name, f'ENTER_{self.curr_mode.upper()}_MODE', 'kickstart'))
        self.logger.debug(f'kickstarting RunnerWorker with ENTER_{self.curr_mode.upper()}_MODE')


    def main_func(self):
        self.logger.debug(f"Entering RunnerWorker.main_func")
        if dt.datetime.now() > self.die_time:
            self.logger.debug(f"RunnerWorker injected a HARD_SHUTDOWN into the event queue")
            self.event_q.safe_put(mptools.EventMessage(self.name, 'HARD_SHUTDOWN', 'die_time exceeded'))

        # if time.time() > self.status_report_deadline:
        #     self.status_queue.safe_put(self.status_report())
        #     self.status_report_deadline = time.time() + self.STATUS_INTERVAL

        for event_type in self.event_types:
            if os.path.exists(os.path.join(self.defs.HOME_DIR, event_type)):
                os.remove(os.path.join(self.defs.HOME_DIR, event_type))
                self.logger.debug(f"RunnerWorker injected an {event_type} message into the event queue")
                self.event_q.safe_put(mptools.EventMessage(self.name, f'{event_type}',
                                                           f'{event_type} override detected'))

        event = self.event_q.safe_get()
        if event:
            self.logger.debug(f'Runner received event: {event}')
            self.last_event = event
        if not event:
            self.verify_mode()
        elif event.msg_type == 'NOTIFY':
            self.main_ctx.notification_q.safe_put(notifier.Notification(event.msg_src, *event.msg))
        elif event.msg_type == 'FATAL':
            self.logger.info(f'{event.msg_type.title()} event received. Rebooting machine')
            note = notifier.Notification(event.msg_src, event.msg_type, event.msg, self.defs.SUMMARY_LOG_FILE)
            self.main_ctx.notification_q.safe_put(note)
            sp.run(['sudo', 'shutdown', '-r', '+5'])
            self.hard_shutdown()
        elif event.msg_type in 'HARD_SHUTDOWN':
            self.logger.info(f'{event.msg_type} event received. Executing hard shutdown')
            self.hard_shutdown()
        elif event.msg_type == 'SOFT_SHUTDOWN':
            self.logger.info(f'{event.msg_type} event received. Executing soft shutdown')
            self.soft_shutdown()
        elif event.msg_type == 'ENTER_ACTIVE_MODE':
            self.logger.info(f'{event.msg_type} event received. Switching to active mode')
            self.active_mode()
        elif event.msg_type == 'ENTER_PASSIVE_MODE':
            self.logger.info(f'{event.msg_type} event received. Switching to passive mode in 10 seconds')
            self.passive_mode()
        elif event.msg_type == 'ENTER_END_MODE':
            self.logger.info(f'{event.msg_type} event received. Exiting collection and uploading all remaining data')
            self.end_mode()
        elif event.msg_type == 'MOCK_HIT':
            self.logger.info(f'{event.msg_type} event received. Forcing the hit response')
            self.mock_hit()
        else:
            self.logger.error(f"Unknown Event: {event}")
        self.logger.debug(f"exiting RunnerWorker.main_func")

    def shutdown(self):
        self.hard_shutdown()

    def verify_mode(self):
        if self.curr_mode == 'active':
            if self.expected_mode() == 'passive':
                self.event_q.safe_put(mptools.EventMessage(self.name, 'ENTER_PASSIVE_MODE', 'mode switch'))
            else:
                time.sleep(0.1)
        elif self.curr_mode == 'passive':
            if self.expected_mode() == 'active':
                self.event_q.safe_put(mptools.EventMessage(self.name, 'ENTER_ACTIVE_MODE', 'mode switch'))
            else:
                sleep_time = self.sleep_until_morning()
                self.logger.info(f'no change in mode. going back to sleep for {sleep_time} seconds')
                pathlib.Path(self.defs.PROJ_JSON_FILE).touch()

                time.sleep(sleep_time)

    def expected_mode(self):
        if self.metadata['source'] or self.metadata['demo'] or self.metadata['test']:
            try:
                return self.curr_mode
            except AttributeError:
                return 'active'
        elif self.defs.START_HOUR <= dt.datetime.now().hour < self.defs.END_HOUR:
            return 'active'
        else:
            return 'passive'

    def switch_mode(self, target_mode):
        if self.curr_mode == target_mode and self.secondary_ctx is not None:
            self.logger.debug(f'runner received instructions to switch to {target_mode} mode, but was already in '
                              f'{self.curr_mode} mode. Skipping mode switch.')
            return
        self.clean_event_queue()
        self.soft_shutdown()
        self.secondary_ctx = mptools.SecondaryContext(self.metadata, self.event_q,
                                                      f'{target_mode.upper()}CONTEXT')
        self.curr_mode = target_mode

    def active_mode(self):
        self.switch_mode('active')
        self.img_q = self.secondary_ctx.MPQueue(maxsize=30)
        if self.metadata['source']:
            self.secondary_ctx.Proc('COLLECT', collector.SourceCollectorWorker, self.img_q, self.metadata['source'])
        elif not self.metadata['model_id']:
            self.secondary_ctx.Proc('COLLECT', collector.SimpleCollectorWorker, self.img_q)
        else:
            self.secondary_ctx.Proc('COLLECT', collector.CollectorWorker, self.img_q)
        if self.metadata['model_id']:
            self.secondary_ctx.Proc('DETECT', detector.DetectorWorker, self.img_q)
        else:
            self.logger.debug('model_id not set, skipping detector initialization')
        self.logger.info('successfully entered active mode')

    def passive_mode(self):
        self.switch_mode('passive')
        time.sleep(10)
        self.upload_q = self.secondary_ctx.MPQueue()
        n_workers = self.queue_uploads()
        for i in range(n_workers):
            self.secondary_ctx.Proc(f'UPLOAD{i+1}', uploader.UploaderWorker, self.upload_q)
        self.logger.info('successfully entered passive mode')

    def hard_shutdown(self):
        self.soft_shutdown()
        self.main_ctx.stop_all_procs()
        self.main_ctx.stop_all_queues()
        self.logger.info(f'Program exiting')

    def soft_shutdown(self):
        tries_left = self.defs.MAX_TRIES
        if not self.secondary_ctx:
            self.logger.debug('secondary context has already been shut down')
            return
        while tries_left:
            tries_left -= 1
            if self.secondary_ctx.procs or self.secondary_ctx.queues:
                try:
                    self.secondary_ctx.stop_all_procs()
                    self.secondary_ctx.stop_all_queues()
                except Exception as e:
                    self.logger.warning(f'soft shutdown failed with error {e}. Trying {tries_left} more times before '
                                        f'executing a hard shutdown')
            else:
                break
        else:
            self.logger.warning('soft shutdown of secondary context failed the maximum number of times. To prevent'
                                'zombie processes, the application will now exit, reboot this machine, and attempt'
                                'to resume.')
            self.event_q.safe_put(mptools.EventMessage(self.name, 'FATAL', 'soft shutdown failed'))
            return

        self.logger.debug('secondary context successfully shut down')
        self.secondary_ctx = None
        self.event_q.drain()

    def mock_hit(self):
        if self.curr_mode != 'active':
            self.logger.warning('cannot inject a mock hit while in passive mode. '
                                'Please switch to active mode and try again')
        else:
            self.img_q.safe_put((gen_utils.current_time_ms(), 'MOCK_HIT'))

    def sleep_until_morning(self):
        """returns a positive sleep time, not exceeding the time until lights on (as specified by START_HOUR in the
        advanced config), but also no longer than 600 seconds. This function can be used to sleep a process for ten
        minute intervals until morning, with a relatively small margin of error.
        :return: time (in seconds) to sleep. Always less than 600 (10 minutes) and less than the time until START_HOUR
        :rtype: float
        """
        if self.metadata['source'] or self.metadata['demo'] or self.metadata['test']:
            return 30
        curr_time = dt.datetime.now()
        if self.defs.START_HOUR <= curr_time.hour < self.defs.END_HOUR:
            return 0
        if curr_time.hour >= self.defs.END_HOUR:
            curr_time = (curr_time + dt.timedelta(days=1))
        next_start = curr_time.replace(hour=self.defs.START_HOUR, minute=0, second=0, microsecond=0)
        return gen_utils.sleep_secs(600, next_start.timestamp())

    def queue_uploads(self, proj_id=None, queue_end_signals=True):
        if not proj_id:
            proj_id = self.metadata['proj_id']
        proj_dir = definitions.PROJ_DIR(proj_id)
        proj_log_dir = definitions.PROJ_LOG_DIR(proj_id)
        proj_vid_dir = definitions.PROJ_VID_DIR(proj_id)
        proj_img_dir = definitions.PROJ_IMG_DIR(proj_id)

        if os.path.exists(proj_log_dir):
            shutil.rmtree(proj_log_dir)
        shutil.copytree(self.defs.LOG_DIR, proj_log_dir)

        upload_list = []
        upload_list.extend(glob.glob(os.path.join(proj_log_dir, '*.log')))
        upload_list.extend(glob.glob(os.path.join(proj_vid_dir, '*.h264')))
        upload_list.extend(glob.glob(os.path.join(proj_vid_dir, '*.mp4')))
        upload_list.extend(glob.glob(os.path.join(proj_img_dir, '*.mp4')))
        upload_list.extend(glob.glob(os.path.join(proj_img_dir, '*.jpg')))
        upload_list.extend(glob.glob(os.path.join(proj_dir, '*.json')))
        n_workers = min(self.MAX_UPLOAD_WORKERS, len(upload_list))
        if upload_list:
            [self.upload_q.safe_put(upload) for upload in upload_list]
        if queue_end_signals:
            [self.upload_q.safe_put('END') for _ in range(n_workers)]
        return n_workers

    def end_mode(self):
        if self.curr_mode == 'passive' and self.secondary_ctx:
            self.logger.info('allowing current upload to finish')
            self.secondary_ctx.stop_procs(stop_wait_secs=600)

        self.switch_mode('end')
        self.upload_q = self.secondary_ctx.MPQueue()
        proj_ids = os.listdir(self.defs.DATA_DIR)
        if not proj_ids:
            self.logger.info('no remaining data to upload. exiting')
            return

        self.logger.info(f'uploading data for: {" ".join(proj_ids)}')
        sp.run(['echo', 'uploading' 'data' 'for:'] + proj_ids)
        [self.queue_uploads(p, False) for p in proj_ids[:-1]]
        self.queue_uploads(proj_ids[-1])
        upload_procs = [self.secondary_ctx.Proc(f'UPLOAD{i + 1}', uploader.EndUploaderWorker, self.upload_q)
                        for i in range(self.MAX_UPLOAD_WORKERS)]
        self.secondary_ctx.stop_procs(upload_procs, stop_wait_secs=3600)
        self.secondary_ctx.stop_all_procs()
        file_utils.remove_empty_dirs(self.defs.DATA_DIR)
        sp.run(['echo', 'upload', 'complete.', 'exiting'])
        self.event_q.safe_put(mptools.EventMessage(self.name, 'HARD_SHUTDOWN', 'project ending'))

    def clean_event_queue(self):
        kept_events = []
        tossed_events = []
        while True:
            event = self.event_q.safe_get()
            if not event:
                break
            elif event.msg_type in ['NOTIFY']:
                kept_events.append(event)
            else:
                tossed_events.append(event)
        if tossed_events:
            tossed_events_str = "\n\t".join([event.msg for event in tossed_events])
            self.logger.debug(f'Tossing the following events without acting on them:\n {tossed_events_str}')
        if kept_events:
            kept_events_str = "\n\t".join([event.msg for event in kept_events])
            self.logger.debug(f'Returning the following events to the event queue:\n {kept_events_str}')
            [self.event_q.safe_put(event) for event in kept_events]

    # def status_report(self):
    #     # TODO: write a function to gather status information about the program into a dict. Possible items:
    #         # self.main_ctx.shutdown_event.is_set()
    #         # self.curr_mode
    #         # self.last_event
    #         # for proc in self.main_ctx.procs:
    #             # proc.start_event.is_set()
    #             # proc.name
    #     pass
