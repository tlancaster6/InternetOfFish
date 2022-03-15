import argparse, time, logging
import os.path
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
print(sys.path)
from internet_of_fish.modules import mptools, collector, detector, definitions



"""
python3 main.py --pid test_project --model mobilenetv2 
"""

def main(params):
    proj_id, model_id, kill_after = params.proj_id, params.model_id, params.kill_after
    with mptools.MainContext(params) as main_ctx:
        if kill_after:
            die_time = time.time() + kill_after
            main_ctx.logger.log(logging.DEBUG, f"Application will be killed in {kill_after} seconds")
        else:
            die_time = None

        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)

        img_q = main_ctx.MPQueue()
        # send_q = main_ctx.MPQueue()
        # reply_q = main_ctx.MPQueue()

        main_ctx.Proc('COLLECT', collector.CollectorWorker, img_q)
        main_ctx.Proc('DETECT', detector.DetectorWorker, img_q)

        while not main_ctx.shutdown_event.is_set():
            if die_time and time.time() > die_time:
                break
            event = main_ctx.event_queue.safe_get()
            if not event:
                continue
            # elif event.msg_type == "STATUS":
            #     send_q.put(event)
            # elif event.msg_type == "OBSERVATION":
            #     send_q.put(event)
            # elif event.msg_type == "ERROR":
            #     send_q.put(event)
            # elif event.msg_type == "REQUEST":
            #     request_handler(event, reply_q, main_ctx)
            elif event.msg_type == "FATAL":
                main_ctx.logger.log(logging.INFO, f"Fatal Event received: {event.msg}")
                break
            elif event.msg_type == "END":
                main_ctx.logger.log(logging.INFO, f"End Event received: {event.msg}")
                break
            elif event.msg_type == "SHUTDOWN":
                main_ctx.logger.log(logging.INFO, f"Shutdown Event received: {event.msg}")
                break
            else:
                main_ctx.logger.log(logging.ERROR, f"Unknown Event: {event}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proj_id', help='project id')
    parser.add_argument('--model_id', help='name of the model')
    parser.add_argument('--kill_after', default=None, type=int, help='optional. kill after specified number of seconds')
    params = parser.parse_args()
    main(params)
