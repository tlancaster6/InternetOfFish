import logging
import time

from context import mptools, utils
import pytest
from io import StringIO
from PIL import Image
from numpy.random import rand
import multiprocessing as mp

# MPQueue testing

def random_image():
    imarray = rand(100, 100, 3) * 255
    im = Image.fromarray(imarray.astype('uint8')).convert('RGB')
    return im


@pytest.fixture
def explicit_mpqueue():
    q = mptools.MPQueue()
    yield q
    if not q._closed:
        q.drain()
        q.safe_close()


@pytest.fixture
def explicit_img_queue():
    q = mptools.MPQueue()
    cap_time = utils.current_time_ms()
    for _ in range(10):
        img = random_image()
        q.safe_put((cap_time, img))
        cap_time += 500
    yield q
    if not q._closed:
        q.drain()
        q.safe_close()


@pytest.mark.parametrize('item', ['a', 1.1, random_image()])
def test_mpqueu_safe_put(explicit_mpqueue, item):
    assert explicit_mpqueue.safe_put(item)


@pytest.mark.parametrize('item', ['a', 1.1, random_image()])
def test_mpqueue_safe_get(explicit_mpqueue, item):
    explicit_mpqueue.safe_put(item)
    ret_item = explicit_mpqueue.safe_get()
    assert ret_item == item


def test_mpqueue_safe_get_empty(explicit_mpqueue):
    assert explicit_mpqueue.safe_get() is None


def test_mpqueue_drain(explicit_img_queue):
    explicit_img_queue.drain()
    explicit_img_queue.safe_get()
    assert explicit_img_queue.safe_get() is None


def test_mpqueue_safe_close(explicit_img_queue):
    explicit_img_queue.safe_close()
    assert explicit_img_queue._closed


# Proc testing
@pytest.fixture
def explicit_proc(mocker):
    mocker.patch('context.utils.LOG_LEVEL', logging.DEBUG)
    proc = mptools.Proc('test_proc', mptools.ProcWorker, mp.Event(), mptools.MPQueue(), {})
    yield proc
    proc.full_stop()


def test_proc_init(explicit_proc, capsys):
    proc = explicit_proc
    start = time.time()
    out = ''
    while (time.time()-start < 10) and ('Proc.__init__ starting : test_proc got True' not in out):
        time.sleep(1)

    assert 'Proc.__init__ starting : test_proc got True' in out









