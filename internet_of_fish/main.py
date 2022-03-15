import argparse, time, logging
import os.path
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from internet_of_fish.modules.collector import CollectorWorker
from internet_of_fish.modules.detector import DetectorWorker
from internet_of_fish.modules.contexts import MainContext
import internet_of_fish.modules.signals as iof_signals



"""
python3 main.py --pid test_project --model mobilenetv2 
"""

def main(args):
    proj_id, model_id, kill_after = args.proj_id, args.model_id, args.kill_after
    with MainContext() as main_ctx:
        if kill_after:
            die_time = time.time() + kill_after
            main_ctx.log(logging.DEBUG, f"Application will be killed in {kill_after} seconds")
        else:
            die_time = None

        iof_signals.init_signals(main_ctx.shutdown_event,
                                 iof_signals.default_signal_handler,
                                 iof_signals.default_signal_handler)

        img_q = main_ctx.MPQueue()
        # send_q = main_ctx.MPQueue()
        # reply_q = main_ctx.MPQueue()

        main_ctx.Proc('COLLECT', CollectorWorker, img_q, proj_id)
        main_ctx.Proc('DETECT', DetectorWorker, img_q, proj_id, model_id)

        while not main_ctx.shutdown_event.is_set():
            if die_time and time.time() > die_time:
                main_ctx.shutdown_event.set()
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
            # elif event.msg_type == "FATAL":
            #     main_ctx.log(logging.INFO, f"Fatal Event received: {event.msg}")
            #     break
            # elif event.msg_type == "END":
            #     main_ctx.log(logging.INFO, f"Shutdown Event received: {event.msg}")
            #     break
            # else:
            #     main_ctx.log(logging.ERROR, f"Unknown Event: {event}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proj_id', help='project id')
    parser.add_argument('--model_id', help='name of the model')
    parser.add_argument('--kill_after', default=None, type=int, help='optional. kill after specified number of seconds')
    args = parser.parse_args()
    main(args)
