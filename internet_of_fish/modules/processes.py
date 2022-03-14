import functools, logging, time
import multiprocessing as mp
from internet_of_fish.modules.utils import _logger
from internet_of_fish.modules import definitions

def proc_worker_wrapper(proc_worker_class, name, startup_evt, shutdown_evt, event_q, *args):
    proc_worker = proc_worker_class(name, startup_evt, shutdown_evt, event_q, *args)
    return proc_worker.run()


class Proc:
    STARTUP_WAIT_SECS = definitions.STARTUP_WAIT_SECS
    SHUTDOWN_WAIT_SECS = definitions.SHUTDOWN_WAIT_SECS

    def __init__(self, name, worker_class, shutdown_event, event_q, *args):
        self.log = functools.partial(_logger, f'{name} Worker')
        self.name = name
        self.shutdown_event = shutdown_event
        self.startup_event = mp.Event()
        self.proc = mp.Process(target=proc_worker_wrapper,
                               args=(worker_class, name, self.startup_event, shutdown_event, event_q, *args))
        self.log(logging.DEBUG, f"Proc.__init__ starting : {name}")
        self.proc.start()
        started = self.startup_event.wait(timeout=Proc.STARTUP_WAIT_SECS)
        self.log(logging.DEBUG, f"Proc.__init__ starting : {name} got {started}")
        if not started:
            self.terminate()
            raise RuntimeError(f"Process {name} failed to startup after {Proc.STARTUP_WAIT_SECS} seconds")

    def full_stop(self, wait_time=SHUTDOWN_WAIT_SECS):
        self.log(logging.DEBUG, f"Proc.full_stop stoping : {self.name}")
        self.shutdown_event.set()
        self.proc.join(wait_time)
        if self.proc.is_alive():
            self.terminate()

    def terminate(self):
        self.log(logging.DEBUG, f"Proc.terminate terminating : {self.name}")
        NUM_TRIES = 3
        tries = NUM_TRIES
        while tries and self.proc.is_alive():
            self.proc.terminate()
            time.sleep(0.01)
            tries -= 1

        if self.proc.is_alive():
            self.log(logging.ERROR, f"Proc.terminate failed to terminate {self.name} after {NUM_TRIES} attempts")
            return False
        else:
            self.log(logging.INFO, f"Proc.terminate terminated {self.name} after {NUM_TRIES - tries} attempt(s)")
            return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.full_stop()
        return not exc_type