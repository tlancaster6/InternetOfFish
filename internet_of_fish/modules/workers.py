import logging, functools, sys, time, io, os
from internet_of_fish.modules.signals import default_signal_handler, init_signals, EventMessage, TerminateInterrupt
from internet_of_fish.modules.utils import _logger, _sleep_secs, _current_time_ms, _current_time_iso
from internet_of_fish.modules import definitions
import picamera
from PIL import Image, ImageDraw
from collections import namedtuple



def request_handler(event, reply_q, main_ctx):
    main_ctx.log(logging.DEBUG, f"request_handler - '{event.msg}'")
    if event.msg == "REQUEST END":
        main_ctx.log(logging.DEBUG, "request_handler - queued END event")
        main_ctx.event_queue.safe_put(EventMessage("request_handler", "END", "END"))

    reply = f'REPLY {event.id} {event.msg}'
    reply_q.safe_put(reply)


class ProcWorker:
    MAX_TERMINATE_CALLED = definitions.MAX_TERMINATE_CALLED
    DATA_DIR = definitions.DATA_DIR
    int_handler = staticmethod(default_signal_handler)
    term_handler = staticmethod(default_signal_handler)

    def __init__(self, name, startup_event, shutdown_event, event_q, *args):
        self.name = name
        self.log = functools.partial(_logger, f'{self.name} Worker')
        self.startup_event = startup_event
        self.shutdown_event = shutdown_event
        self.event_q = event_q
        self.terminate_called = 0
        self.init_args(args)

    def init_args(self, args):
        if args:
            raise ValueError(f"Unexpected arguments to ProcWorker.init_args: {args}")

    def init_signals(self):
        self.log(logging.DEBUG, "Entering init_signals")
        signal_object = init_signals(self.shutdown_event, self.int_handler, self.term_handler)
        return signal_object

    def main_loop(self):
        self.log(logging.DEBUG, "Entering main_loop")
        while not self.shutdown_event.is_set():
            self.main_func()

    def startup(self):
        self.log(logging.DEBUG, "Entering startup")
        pass

    def shutdown(self):
        self.log(logging.DEBUG, "Entering shutdown")
        pass

    def main_func(self, *args):
        self.log(logging.DEBUG, "Entering main_func")
        raise NotImplementedError(f"{self.__class__.__name__}.main_func is not implemented")

    def run(self):
        self.init_signals()
        try:
            self.startup()
            self.startup_event.set()
            self.main_loop()
            self.log(logging.INFO, "Normal Shutdown")
            self.event_q.safe_put(EventMessage(self.name, "SHUTDOWN", "Normal"))
            return 0
        except BaseException as exc:
            # -- Catch ALL exceptions, even Terminate and Keyboard interrupt
            self.log(logging.ERROR, f"Exception Shutdown: {exc}", exc_info=True)
            self.event_q.safe_put(EventMessage(self.name, "FATAL", f"{exc}"))
            # -- TODO: call raise if in some sort of interactive mode
            if type(exc) in (TerminateInterrupt, KeyboardInterrupt):
                sys.exit(1)
            else:
                sys.exit(2)
        finally:
            self.shutdown()


class TimerProcWorker(ProcWorker):
    """performs main loop every INTERVAL_SECS"""
    INTERVAL_SECS = 10
    MAX_SLEEP_SECS = 0.02

    def main_loop(self):
        self.log(logging.DEBUG, "Entering TimerProcWorker.main_loop")
        next_time = time.time() + self.INTERVAL_SECS
        while not self.shutdown_event.is_set():
            sleep_secs = _sleep_secs(self.MAX_SLEEP_SECS, next_time)
            time.sleep(sleep_secs)
            if time.time() > next_time:
                self.log(logging.DEBUG, f"TimerProcWorker.main_loop : calling main_func")
                self.main_func()
                next_time = time.time() + self.INTERVAL_SECS


class QueueProcWorker(ProcWorker):
    def init_args(self, args):
        self.log(logging.DEBUG, f"Entering QueueProcWorker.init_args : {args}")
        self.work_q, = args

    def main_loop(self):
        self.log(logging.DEBUG, "Entering QueueProcWorker.main_loop")
        while not self.shutdown_event.is_set():
            item = self.work_q.safe_get()
            if not item:
                continue
            self.log(logging.DEBUG, f"QueueProcWorker.main_loop received '{item}' message")
            if item == "END":
                break
            else:
                self.main_func(item)








class ListenWorker(ProcWorker):
    SOCKET_TIMEOUT = 1.0

    def init_args(self, args):
        self.reply_q, = args

    def startup(self):
        # -- Called during worker process start up sequence
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('127.0.0.1', 9999))
        self.socket.settimeout(self.SOCKET_TIMEOUT)
        self.socket.listen(1)

    def shutdown(self):
        # -- Called when worker process is shutting down
        self.socket.close()

    def _test_hook(self):
        # -- method intended to be overriden during testing, allowing testing
        # to interact with the main_func
        pass

    def main_func(self):
        # -- Handle one connection from a client.  Each connection will
        # handle exactly ONE request and its reply
        try:
            (clientsocket, address) = self.socket.accept()
        except socket.timeout:
            return

        # TODO: handle timeout conditions better
        self.log(logging.INFO, f"Accepted connection from {address}")
        try:
            clientsocket.settimeout(self.SOCKET_TIMEOUT)
            buffer = clientsocket.recv(1500).decode()
            self.log(logging.DEBUG, f"Received {buffer}")
            self.event_q.put(EventMessage("LISTEN", "REQUEST", buffer))
            self._test_hook()
            reply = self.reply_q.safe_get(timeout=self.SOCKET_TIMEOUT)
            self.log(logging.DEBUG, f"Sending Reply {reply}")
            clientsocket.send(reply.encode("utf-8"))
        finally:
            clientsocket.close()


class StatusWorker(TimerProcWorker):
    def startup(self):
        self.last_status = None

    def get_status(self):
        return "OKAY" if random.randrange(10) else "NOT-OKAY"

    def main_func(self):
        # -- Do the things to check current status, only send the status message
        # if status has changed
        curr_status = self.get_status()
        if curr_status != self.last_status:
            self.event_q.put(EventMessage(self.name, "STATUS", curr_status))
            self.last_status = curr_status


class ObservationWorker(TimerProcWorker):
    def main_func(self):
        # -- Do the things to obtain a current observation
        self.event_q.put(EventMessage(self.name, "OBSERVATION", "SOME DATA"))


class SendWorker(QueueProcWorker):
    def startup(self):
        self.send_file = open("send_file.txt", "a")

    def shutdown(self):
        self.send_file.close()

    def main_func(self, data):
        # -- Write the messages to the log file.
        self.send_file.write(f'{data.msg_type}::{data.msg}\n')
        self.send_file.flush()
