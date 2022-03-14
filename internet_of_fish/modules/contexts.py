import logging, functools, time
import multiprocessing as mp
from internet_of_fish.modules.utils import _logger, _sleep_secs
from internet_of_fish.modules.processes import Proc
from internet_of_fish.modules.queues import MPQueue
from internet_of_fish.modules.signals import EventMessage
from internet_of_fish.modules import definitions

class MainContext:
    STOP_WAIT_SECS = definitions.STOP_WAIT_SECS

    def __init__(self):
        self.procs = []
        self.queues = []
        self.log = functools.partial(_logger, "MAIN")
        self.shutdown_event = mp.Event()
        self.event_queue = self.MPQueue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log(logging.ERROR, f"Exception: {exc_val}", exc_info=(exc_type, exc_val, exc_tb))

        self._stopped_procs_result = self.stop_procs()
        self._stopped_queues_result = self.stop_queues()

        # -- Don't eat exceptions that reach here.
        return not exc_type

    def Proc(self, name, worker_class, *args):
        proc = Proc(name, worker_class, self.shutdown_event, self.event_queue, *args)
        self.procs.append(proc)
        return proc

    def MPQueue(self, *args, **kwargs):
        q = MPQueue(*args, **kwargs)
        self.queues.append(q)
        return q

    def stop_procs(self):
        self.event_queue.safe_put(EventMessage("stop_procs", "END", "END"))
        self.shutdown_event.set()
        end_time = time.time() + self.STOP_WAIT_SECS
        num_terminated = 0
        num_failed = 0

        # -- Wait up to STOP_WAIT_SECS for all processes to complete
        for proc in self.procs:
            join_secs = _sleep_secs(self.STOP_WAIT_SECS, end_time)
            proc.proc.join(join_secs)

        # -- Clear the procs list and _terminate_ any procs that
        # have not yet exited
        still_running = []
        while self.procs:
            proc = self.procs.pop()
            if proc.proc.is_alive():
                if proc.terminate():
                    num_terminated += 1
                else:
                    still_running.append(proc)
            else:
                exitcode = proc.proc.exitcode
                if exitcode:
                    self.log(logging.ERROR, f"Process {proc.name} ended with exitcode {exitcode}")
                    num_failed += 1
                else:
                    self.log(logging.DEBUG, f"Process {proc.name} stopped successfully")

        self.procs = still_running
        return num_failed, num_terminated

    def stop_queues(self):
        num_items_left = 0
        # -- Clear the queues list and close all associated queues
        for q in self.queues:
            num_items_left += sum(1 for __ in q.drain())
            q.close()

        # -- Wait for all queue threads to stop
        while self.queues:
            q = self.queues.pop(0)
            q.join_thread()
        return num_items_left