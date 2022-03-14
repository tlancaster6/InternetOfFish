import multiprocessing as mp
import multiprocessing.queues as mpq
import time
from queue import Full, Empty
from internet_of_fish.modules import definitions

DEFAULT_POLLING_TIMEOUT = definitions.DEFAULT_POLLING_TIMEOUT


class MPQueue(mpq.Queue):

    # -- See StackOverflow Article :
    #   https://stackoverflow.com/questions/39496554/cannot-subclass-multiprocessing-queue-in-python-3-5
    #
    # -- tldr; mp.Queue is a _method_ that returns an mpq.Queue object.  That object
    # requires a context for proper operation, so this __init__ does that work as well.
    def __init__(self, *args, **kwargs):
        ctx = mp.get_context()
        super().__init__(*args, **kwargs, ctx=ctx)

    def safe_get(self, timeout=DEFAULT_POLLING_TIMEOUT):
        try:
            if timeout is None:
                return self.get(block=False)
            else:
                return self.get(block=True, timeout=timeout)
        except Empty:
            return None

    def safe_put(self, item, timeout=DEFAULT_POLLING_TIMEOUT):
        try:
            self.put(item, block=False, timeout=timeout)
            return True
        except Full:
            return False

    def drain(self):
        item = self.safe_get()
        while item:
            yield item
            item = self.safe_get()

    def safe_close(self):
        num_left = sum(1 for __ in self.drain())
        self.close()
        self.join_thread()
        return num_left
