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
def explicit_img_queue(explicit_mpqueue):
    cap_time = utils.current_time_ms()
    for _ in range(10):
        img = random_image()
        explicit_mpqueue.safe_put((cap_time, img))
        cap_time += 500
    yield explicit_mpqueue


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


def test_mpqueue_drain(explicit_mpqueue):
    for i in range(10):
        explicit_mpqueue.safe_put(i)
    time.sleep(1)
    explicit_mpqueue.drain()
    assert explicit_mpqueue.safe_get() is None


def test_mpqueue_safe_close(explicit_mpqueue):
    for i in range(10):
        explicit_mpqueue.safe_put(i)
    explicit_mpqueue.safe_close()
    assert explicit_mpqueue._closed


# Proc testing
@pytest.fixture
def explicit_proc_with_stdout_mocker(mocker):
    mocker.patch('context.utils.LOG_LEVEL', logging.DEBUG)
    stdout_mocker = mocker.patch('sys.stdout', new_callable=StringIO)
    proc = mptools.Proc('test_proc', mptools.Proc, mp.Event(), mptools.MPQueue(), {})
    yield proc, stdout_mocker
    proc.full_stop()
    stdout_mocker.close()


def test_proc_init(explicit_proc):
    proc, stdout_mocker = explicit_proc
    start = time.time()
    out = ''
    while (time.time()-start < 10) and ('Proc.__init__ starting : test_proc got True' not in out):
        out = out + stdout_mocker.get_value()
    assert 'Proc.__init__ starting : test_proc got True' in out









