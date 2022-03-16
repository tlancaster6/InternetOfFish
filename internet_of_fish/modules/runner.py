from internet_of_fish.modules import mptools, collector, detector, utils, uploader
import time, logging


def active_mode(params):
    with mptools.MainContext(params) as main_ctx:
        main_ctx.logger.log(logging.INFO, "Application entering active mode")
        # set up a timed kill condition, if necessary
        if params.kill_after:
            die_time = time.time() + params.kill_after
            main_ctx.logger.log(logging.INFO, f"Application will be killed in {params.kill_after} seconds")
        else:
            die_time = None

        # initialize important objects (signals, queues, processes, etc)
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        img_q = main_ctx.MPQueue()
        if params.source:
            main_ctx.Proc('COLLECT', collector.VideoCollectorWorker, img_q, params.source)
        else:
            main_ctx.Proc('COLLECT', collector.CollectorWorker, img_q)
        main_ctx.Proc('DETECT', detector.DetectorWorker, img_q)

        # keep checking the event queue until this loop gets broken
        while not main_ctx.shutdown_event.is_set():
            # if die_time is exceeded, put a SHUTDOWN signal in the event queue
            if die_time and time.time() > die_time:
                main_ctx.event_queue.safe_put(mptools.EventMessage('main.py', 'SHUTDOWN', 'kill_after condition reached'))
            # read an event from the event_queue and act accordingly
            event = main_ctx.event_queue.safe_get()
            if not event:
                time.sleep(0.1)
            elif event.msg_type == "FATAL":
                main_ctx.logger.log(logging.INFO, f"Fatal Event received: {event.msg}")
                break
            elif event.msg_type == "SHUTDOWN":
                main_ctx.logger.log(logging.INFO, f"Shutdown Event received: {event.msg}")
                break
            else:
                main_ctx.logger.log(logging.ERROR, f"Unknown Event: {event}")

        if params.source or params.kill_after:
            main_ctx.logger.log(logging.INFO, f'exiting application because either source or kill_after was set')
            return
        elif event and event.msg_type == 'FATAL':
            main_ctx.logger.log(logging.INFO, f'exiting application due to fatal error')
            return
        else:
            main_ctx.logger.log(logging.INFO, f'entering passive mode in ten seconds')
            time.sleep(10)
    passive_mode(params)


def passive_mode(params):
    with mptools.MainContext(params) as main_ctx:
        main_ctx.logger.log(logging.INFO, "Application entering passive mode")
        upload_q = main_ctx.MPQueue()
        main_ctx.Proc('UPLOAD', uploader.UploaderWorker, upload_q)

        while not main_ctx.shutdown_event.is_set():
            if utils.lights_on():
                break
            event = main_ctx.event_queue.safe_get()
            if not event:
                sleep_time = utils.sleep_until_morning()
                main_ctx.logger.log(logging.DEBUG, f"Event queue empty. Going back to sleep for {sleep_time} seconds")
                time.sleep(sleep_time)
            else:
                main_ctx.logger.log(logging.ERROR, f"Unknown Event: {event}")
        main_ctx.logger.log(logging.INFO, f'entering active mode')
    active_mode(params)





