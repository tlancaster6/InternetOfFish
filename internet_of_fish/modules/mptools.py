import functools
import logging
import multiprocessing as mp
import multiprocessing.queues as mpq
import signal
import sys
import time
from queue import Empty, Full
from internet_of_fish.modules import utils, definitions
import re
from typing import Union

"""adapted from https://github.com/PamelaM/mptools"""

DEFAULT_POLLING_TIMEOUT = definitions.DEFAULT_POLLING_TIMEOUT
DEFAULT_MAX_SLEEP_SECS = definitions.DEFAULT_MAX_SLEEP_SECS


# -- Queue handling support

class MPQueue(mpq.Queue):

    def __init__(self, *args, **kwargs):
        """
        flexible queue object built on the multiprocessing.queues.Queue class.
        :param args: positional arguments passed to the parent class __init__
        :param kwargs: keyword args passed to the parent class __init__
        """
        ctx = mp.get_context()
        super().__init__(*args, **kwargs, ctx=ctx)

    def safe_get(self, timeout=DEFAULT_POLLING_TIMEOUT):
        """
        similar to the base .get() method, but more robust. In situations where .get() would raise an Empty
        exception, this method catches the exception and returns None. This method also obscures the .get() block
        argument, and prevents it from being set to True when timeout. This avoids the scenario where a call to .get()
        blocks indefinitely, essentially freezing up the queue.
        :param timeout: Max number of seconds to wait for an item to appear in the queue before instead returning None.
               Defaults to DEFAULT_POLLING_TIMEOUT. If set to None,
        :type timeout: float
        :return: returns the next item in the queue, or returns None in the event of an Empty exception
        """
        if self._closed:
            return
        try:
            if timeout is None:
                # get an item from the queue immediately, raise an Empty exception if the queue is currently empty
                return self.get(block=False)
            else:
                # get an item from the queue, waiting up to "timeout" seconds for the queue to be nonempty. Raise an
                # Empty exception after the timeout expires
                return self.get(block=True, timeout=timeout)
        except Empty:
            # catch the Empty exception that might be raised by either of the above self.get calls, and return None
            return None

    def safe_put(self, item, timeout=DEFAULT_POLLING_TIMEOUT):
        """
        similar to the .put() base class, but more robust. In situations where .put() would raise the Full exception,
        this method catches the exception and instead returns False. Also obscures the .put() block keyword argument
        to prevent the safe_put command from blocking indefinitely.
        :param item: item to place in the queue
        :type item: Any
        :param timeout: max time to wait for a spot to open up in the queue before instead returning False
        :type timeout: float
        :return: return True if the item was put in the queue successfully, False if the queue was full
        :rtype: bool
        """
        if self._closed:
            return
        try:
            self.put(item, block=False, timeout=timeout)
            return True
        except Full:
            return False

    def drain(self):
        """
        safely remove all items from the queue without processing them. Useful for smoothly shutting down other
        processes that are using a queue.
        """
        item = self.safe_get()
        while item is not None:
            print(item)
            yield item
            item = self.safe_get()

    def safe_close(self):
        """
        safely drain the queue, then close it, then join the thread to free up resources. Returns the number of items
        that were drained from the queue, which may be diagnostically helpful in some contexts.
        :return: the number of items that were drained from the queue and discarded before exiting
        :rtype: int
        """
        num_left = sum(1 for __ in self.drain())
        self.close()
        self.join_thread()
        return num_left


# -- useful function
def sleep_secs(max_sleep, end_time=999999999999999.9):
    """
    Calculate time left to sleep in seconds. The returned value will be >=0, <=max_sleep, and will never exceed the
    number of seconds between the current time and the specified end_time.
    :param max_sleep: max sleep time. Useful for enforcing that a process checks in periodically to see if it needs to
                      wake up. units: seconds
    :type max_sleep: float
    :param end_time: the return value of this function will never exceed the difference between the current time and
                     this time. Useful for setting a hard limit on end time. Expressed in seconds since epoch, like the
                     return value from time.time(). Defaults to a number large enough to be many years in the future
                     regardless of operating system
    :type end_time: float
    :return: sleep time, in seconds, such that 0<=ret<=max_sleep and ret<=(end_time=time.time())
    :rtype: float
    """
    return max(0.0, min(end_time - time.time(), max_sleep))


# -- Evemt queue message template
class EventMessage:
    def __init__(self, msg_src, msg_type, msg):
        """
        simple data container of the type expected by an event queue (see MainContext for more detail on event queues)
        :param msg_src: process, class, or function that generated the message.
        :type msg_src: str
        :param msg_type: used to determine the proper response to the message. Common values include 'SOFT_SHUTDOWN' and
                        'FATAL'.
        :type msg_type: str
        :param msg: additional information about the message, used mostly for logging
        :type msg: Union[str, List(str)]

        """
        self.id = time.time()
        self.msg_src = msg_src
        self.msg_type = msg_type
        self.msg = msg

    def __str__(self):
        return f"{self.msg_src:10} - {self.msg_type:10} : {self.msg}"


# -- Signal Handling
class TerminateInterrupt(BaseException):
    pass


class SignalObject:
    MAX_TERMINATE_CALLED = definitions.MAX_TRIES

    def __init__(self, shutdown_event):
        self.terminate_called = 0
        self.shutdown_event = shutdown_event


def default_signal_handler(signal_object, exception_class, signal_num, current_stack_frame):
    signal_object.terminate_called += 1
    signal_object.shutdown_event.set()
    if signal_object.terminate_called >= signal_object.MAX_TERMINATE_CALLED:
        raise exception_class()


def init_signal(signal_num, signal_object, exception_class, handler):
    handler = functools.partial(handler, signal_object, exception_class)
    signal.signal(signal_num, handler)
    signal.siginterrupt(signal_num, False)


def init_signals(shutdown_event, int_handler, term_handler):
    signal_object = SignalObject(shutdown_event)
    init_signal(signal.SIGINT, signal_object, KeyboardInterrupt, int_handler)
    init_signal(signal.SIGTERM, signal_object, TerminateInterrupt, term_handler)
    return signal_object


# -- Worker Process classes

class ProcWorker(metaclass=utils.AutologMetaclass):
    MAX_TERMINATE_CALLED = definitions.MAX_TRIES
    int_handler = staticmethod(default_signal_handler)
    term_handler = staticmethod(default_signal_handler)

    def __init__(self, name, startup_event, shutdown_event, event_q, metadata, *args):
        self.name = name
        self.metadata = metadata
        self.logger = utils.make_logger(name)
        self.startup_event = startup_event
        self.shutdown_event = shutdown_event
        self.event_q = event_q
        self.terminate_called = 0
        self.init_args(args)

    def init_args(self, args):
        if args:
            raise ValueError(f"Unexpected arguments to ProcWorker.init_args: {args}")

    def init_signals(self):
        signal_object = init_signals(self.shutdown_event, self.int_handler, self.term_handler)
        return signal_object

    def main_loop(self):
        while not self.shutdown_event.is_set():
            self.main_func()

    def startup(self):
        pass

    def shutdown(self):
        pass

    def main_func(self, *args):
        raise NotImplementedError(f"{self.__class__.__name__}.main_func is not implemented")

    def run(self):
        self.init_signals()
        try:
            self.startup()
            self.startup_event.set()
            self.main_loop()
            self.logger.log(logging.INFO, "Normal Shutdown")
            return 0
        except BaseException as exc:
            # -- Catch ALL exceptions, even Terminate and Keyboard interrupt
            self.logger.log(logging.ERROR, f"Exception Shutdown: {exc}", exc_info=True)
            self.event_q.safe_put(EventMessage(self.name, "FATAL", f"{exc}"))
        finally:
            self.shutdown()


class TimerProcWorker(ProcWorker, metaclass=utils.AutologMetaclass):
    INTERVAL_SECS = definitions.DEFAULT_INTERVAL_SECS
    MAX_SLEEP_SECS = definitions.DEFAULT_MAX_SLEEP_SECS

    def main_loop(self):
        next_time = time.time() + self.INTERVAL_SECS
        while not self.shutdown_event.is_set():
            time.sleep(sleep_secs(self.MAX_SLEEP_SECS, next_time))
            if time.time() > next_time:
                self.main_func()
                next_time = time.time() + self.INTERVAL_SECS


class QueueProcWorker(ProcWorker, metaclass=utils.AutologMetaclass):
    def init_args(self, args):
        self.work_q, = args

    def main_loop(self):
        while not self.shutdown_event.is_set():
            item = self.work_q.safe_get()
            if not item:
                continue
            self.logger.debug(f"QueueProcWorker.main_loop received '{item}' message")
            if item == "END":
                break
            else:
                self.main_func(item)


# -- Process Wrapper

def proc_worker_wrapper(proc_worker_class, name, startup_evt, shutdown_evt, event_q, metadata, *args):
    proc_worker = proc_worker_class(name, startup_evt, shutdown_evt, event_q, metadata, *args)
    return proc_worker.run()


class Proc(metaclass=utils.AutologMetaclass):
    STARTUP_WAIT_SECS = definitions.DEFAULT_STARTUP_WAIT_SECS
    SHUTDOWN_WAIT_SECS = definitions.DEFAULT_SHUTDOWN_WAIT_SECS

    def __init__(self, name, worker_class, shutdown_event, event_q, metadata, *args):
        self.metadata = metadata
        self.logger = utils.make_logger(name)
        self.name = name
        self.shutdown_event = shutdown_event
        self.startup_event = mp.Event()
        self.proc = mp.Process(target=proc_worker_wrapper,
                               args=(worker_class, name, self.startup_event, shutdown_event, event_q, metadata, *args))
        self.logger.debug(f"Proc.__init__ starting : {name}")
        self.proc.start()
        started = self.startup_event.wait(timeout=Proc.STARTUP_WAIT_SECS)
        self.logger.debug(f"Proc.__init__ starting : {name} got {started}")
        if not started:
            self.terminate()
            raise RuntimeError(f"Process {name} failed to startup after {Proc.STARTUP_WAIT_SECS} seconds")

    def full_stop(self, wait_time=SHUTDOWN_WAIT_SECS):
        self.shutdown_event.set()
        self.proc.join(wait_time)
        if self.proc.is_alive():
            self.terminate()

    def terminate(self):
        NUM_TRIES = 3
        tries = NUM_TRIES
        while tries and self.proc.is_alive():
            self.proc.terminate()
            time.sleep(0.01)
            tries -= 1

        if self.proc.is_alive():
            self.logger.log(logging.ERROR, f"Proc.terminate failed to terminate {self.name} after {NUM_TRIES} attempts")
            return False
        else:
            self.logger.log(logging.INFO, f"Proc.terminate terminated {self.name} after {NUM_TRIES - tries} attempt(s)")
            return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f'Proc.__exit__ called for {self.name}')
        self.full_stop()
        return not exc_type


# -- Main Wrappers
class MainContext(metaclass=utils.AutologMetaclass):
    STOP_WAIT_SECS = definitions.DEFAULT_SHUTDOWN_WAIT_SECS

    def __init__(self, metadata: dict):
        self.metadata = metadata
        self.procs = []
        self.queues = []
        self.shutdown_event = mp.Event()
        self.event_queue = self.MPQueue()
        self._init_specials()

    def _init_specials(self):
        self.notification_q = self.MPQueue()
        self.logger = utils.make_logger('MAINCONTEXT')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug(f'exiting context')
        if exc_type:
            self.logger.log(logging.ERROR, f"Exception: {exc_val}", exc_info=(exc_type, exc_val, exc_tb))
        self._stopped_procs_result = self.stop_all_procs()
        self._stopped_queues_result = self.stop_all_queues()
        self.logger.info('.'*40)

        # -- Don't eat exceptions that reach here.
        return not exc_type

    def Proc(self, name, worker_class, *args, **kwargs):
        """

        :param name:
        :param worker_class:
        :param args:
        :param kwargs:
        :return:
        """
        proc = Proc(name, worker_class, self.shutdown_event, self.event_queue, self.metadata, *args)
        self.procs.append(proc)
        return proc

    def MPQueue(self, *args, **kwargs):
        q = MPQueue(*args, **kwargs)
        self.queues.append(q)
        return q

    def stop_procs(self, procs, stop_wait_secs=None):
        stop_wait_secs = stop_wait_secs if stop_wait_secs else self.STOP_WAIT_SECS
        end_time = time.time() + stop_wait_secs
        num_terminated = 0
        num_failed = 0
        # wait up to STOP_WAIT_SECS for all processes to complete
        for proc in procs:
            join_secs = sleep_secs(stop_wait_secs, end_time)
            self.logger.debug(f'attempting to join {proc.name}. timing out in {join_secs:.2}')
            proc.proc.join(join_secs)
        # quickly try to join each proc once more. Useful for long proc lists with high stop_wait_secs, as some procs
        # may finish after the first join attempt, but before the final join on the final proc times out
        [proc.proc.join(0.2) for proc in procs]
        # terminate any procs that failed to join
        dead_procs = []
        while procs:
            proc = procs.pop()
            if proc.proc.is_alive():
                if proc.terminate():
                    num_terminated += 1
                    dead_procs.append(proc)
            else:
                dead_procs.append(proc)
                exitcode = proc.proc.exitcode
                if exitcode:
                    self.logger.error(f"Process {proc.name} ended with exitcode {exitcode}")
                    num_failed += 1
                else:
                    self.logger.debug(f"Process {proc.name} stopped successfully")

        self.procs = [proc for proc in self.procs if proc not in dead_procs]
        return num_failed, num_terminated

    def stop_procs_by_name(self, name, **kwargs):
        target_procs = [proc for proc in self.procs if re.fullmatch(name, proc.name)]
        if not target_procs:
            self.logger.debug(f'no processes with names matching {name}')
            return
        self.logger.debug(f'stopping {" ".join([proc.name for proc in target_procs])}')
        num_failed, num_terminated = self.stop_procs(target_procs, **kwargs)
        return num_failed, num_terminated

    def stop_all_procs(self, **kwargs):
        self.shutdown_event.set()
        num_failed, num_terminated = self.stop_procs(self.procs, kwargs)
        return num_failed, num_terminated

    def stop_all_queues(self):
        num_items_left = 0
        self.shutdown_event.set()
        # -- Clear the queues list and close all associated queues
        for q in self.queues:
            num_items_left += sum(1 for __ in q.drain())
            q.close()

        # -- Wait for all queue threads to stop
        while self.queues:
            q = self.queues.pop(0)
            q.join_thread()
        return num_items_left


class SecondaryContext(MainContext, metaclass=utils.AutologMetaclass):

    def __init__(self, metadata, event_q=None, name='SECONDARYCONTEXT'):
        self.name = name.upper()
        super().__init__(metadata)
        # the secondary and main contexts usually share the same event queue (achieved by passing the main context
        # event queue as "event_q" during instantiation of the SecondaryContext). Otherwise, default to a new queue
        self.event_queue = event_q if event_q else MPQueue()
        self.logger.debug(f'new SecondaryContext initialized as {name}')

    def _init_specials(self):
        self.logger = utils.make_logger(self.name)

