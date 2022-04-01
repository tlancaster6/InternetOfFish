from typing import Tuple
from internet_of_fish.modules import mptools, collector, detector, utils, uploader, notifier, definitions
import time
import datetime as dt
import os
import glob


class RunnerWorker(mptools.ProcWorker):
    MAX_UPLOAD_WORKERS = definitions.MAX_UPLOAD_WORKERS

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
        self.img_q, self.notification_q, self.upload_q = None, None, None
        self.die_time = dt.datetime.fromisoformat('T'.join([self.metadata['end_date'], self.metadata['end_time']]))
        self.logger.debug(f"RunnerWorker.die_time set to {self.die_time}")
        self.event_q.safe_put(mptools.EventMessage(self.name, f'ENTER_{self.curr_mode.upper()}_MODE', 'kickstart'))
        self.logger.debug(f'kickstarting RunnerWorker with ENTER_{self.curr_mode.upper()}_MODE')
        self.logger.debug(f"Exiting RunnerWorker.startup")


    def main_func(self):
        self.logger.debug(f"Entering RunnerWorker.main_func")
        if dt.datetime.now() > self.die_time:
            self.logger.debug(f"RunnerWorker injected a HARD_SHUTDOWN into the event queue")
            self.event_q.safe_put(mptools.EventMessage(self.name, 'HARD_SHUTDOWN', 'die_time exceeded'))
        if os.path.exists(definitions.END_FILE):
            self.logger.debug(f"RunnerWorker injected an ENTER_END_MODE message into the event queue")
            self.event_q.safe_put(mptools.EventMessage(self.name, 'ENTER_END_MODE', 'END_FILE detected'))

        event = self.event_q.safe_get()
        if event:
            self.logger.debug(f'Runner received event: {event}')
        if not event:
            self.verify_mode()
        elif event.msg_type == 'FATAL':
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Executing hard shutdown')
            self.hard_shutdown()
        elif event.msg_type in 'HARD_SHUTDOWN':
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
        elif event.msg_type == 'ENTER_END_MODE':
            self.logger.info(f'{event.msg.title().replace("_", " ")} event received. Exiting collection and uploading all remaining data')
            self.end_mode()
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
        self.soft_shutdown()
        self.secondary_ctx = mptools.SecondaryContext(self.main_ctx.metadata, self.event_q, 'ACTIVECONTEXT')
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
        self.soft_shutdown()
        self.secondary_ctx = mptools.SecondaryContext(self.main_ctx.metadata, self.event_q, 'PASSIVECONTEXT')
        self.curr_mode = 'passive'
        time.sleep(10)
        self.notification_q = self.secondary_ctx.MPQueue()
        self.notify_proc = self.secondary_ctx.Proc('NOTIFY', notifier.NotifierWorker, self.notification_q)
        self.upload_q = self.secondary_ctx.MPQueue()
        n_workers = self.queue_uploads()
        for i in range(n_workers):
            self.secondary_ctx.Proc(f'UPLOAD{i+1}', uploader.UploaderWorker, self.upload_q)

    def hard_shutdown(self):
        self.soft_shutdown()
        self.logger.debug(f'entering hard_shutdown.')
        self.main_ctx.stop_procs()
        self.main_ctx.stop_queues()
        self.logger.debug(f'exiting hard shutdown.')
        self.logger.info(f'Program exiting')

    def soft_shutdown(self):
        self.logger.debug(f'entering soft_shutdown')
        if not self.secondary_ctx:
            self.logger.debug('secondary context has already been shut down')
            return
        self.secondary_ctx.stop_procs()
        self.secondary_ctx.stop_queues()
        self.secondary_ctx = None
        self.event_q.drain()
        self.logger.debug('exiting soft_shutdown.')

    def sleep_until_morning(self):
        return utils.sleep_until_morning()

    def queue_uploads(self, proj_id=None, queue_end_signals=True):
        proj_id = proj_id if proj_id else self.metadata['proj_id']
        upload_list = []
        proj_dir = os.path.join(definitions.DATA_DIR, proj_id)
        upload_list.extend(glob.glob(os.path.join(proj_dir, '**', '*.h264')))
        upload_list.extend(glob.glob(os.path.join(proj_dir, '**', '*.mp4')))
        upload_list.extend(glob.glob(os.path.join(proj_dir, '*.json')))
        n_workers = min(self.MAX_UPLOAD_WORKERS, len(upload_list))
        if upload_list:
            [self.upload_q.safe_put(upload) for upload in upload_list]
        if queue_end_signals:
            [self.upload_q.safe_put('END') for _ in range(n_workers)]
        return n_workers

    def end_mode(self):
        self.soft_shutdown()
        self.secondary_ctx = mptools.SecondaryContext(self.main_ctx.metadata, self.event_q, 'ENDCONTEXT')
        self.curr_mode = 'end'
        self.upload_q = self.secondary_ctx.MPQueue()
        proj_ids = os.listdir(definitions.DATA_DIR)
        if not proj_ids:
            self.logger.info('no data found to upload. exiting')
            return

        self.logger.info(f'uploading data for: {" ".join(proj_ids)}')
        [self.queue_uploads(p, False) for p in proj_ids[:-1]]
        self.queue_uploads(proj_ids[-1])
        upload_procs = [self.secondary_ctx.Proc(f'UPLOAD{i + 1}', uploader.EndUploaderWorker, self.upload_q)
                        for i in range(self.MAX_UPLOAD_WORKERS)]
        self.wait_for_join(upload_procs)
        utils.remove_empty_dirs(definitions.DATA_DIR)
        os.remove(definitions.END_FILE)
        self.event_q.safe_put(mptools.EventMessage(self.name, 'HARD_SHUTDOWN', 'project ending'))

    def wait_for_join(self, procs, max_wait=3600):
        start = time.time()
        live_procs = []
        while (time.time() - start) < max_wait:
            live_procs = [proc for proc in procs if proc.proc.is_alive()]
            if not live_procs:
                self.logger.info('all processes completed successfully')
                break
            self.logger.info(f'please wait: {len(live_procs)} critical processes still running. '
                             f'automatic timeout in {max_wait - (time.time() - start)} seconds')
            [proc.proc.join(10) for proc in live_procs]
        else:
            self.logger.warning(f'timeout reached with {len(live_procs)} processes still running')





class TestingRunnerWorker(RunnerWorker):
    MODE_SWITCH_INTERVAL = 180

    def init_args(self, args: Tuple[mptools.MainContext,]):
        self.logger.debug(f"Entering RunnerWorker.init_args : {args}")
        self.main_ctx, = args
        self.curr_mode = 'active'
        self.mode_start = time.time()
        self.logger.debug(f"Exiting RunnerWorker.init_args")

    def expected_mode(self):

        mode_map = {'active': 'passive', 'passive': 'active'}
        if (time.time() - self.mode_start) > self. MODE_SWITCH_INTERVAL:
            self.logger.debug(f'switching mode on {self.MODE_SWITCH_INTERVAL//60}-minute marker\n')
            self.mode_start = time.time()
            return mode_map[self.curr_mode]
        else:
            return self.curr_mode

    def sleep_until_morning(self):
        return 10









