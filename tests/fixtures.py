import shutil
import os
import pytest
from PIL import Image
from numpy.random import rand
from context import utils
from context import mptools


@pytest.fixture
def tmp_dir():
    tmp_dir = os.path.realpath('./tmp')
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)
    yield tmp_dir
    shutil.rmtree(tmp_dir)


@pytest.fixture
def tmp_img_dir(tmp_dir):
    for i in range(10):
        imarray = rand(100, 100, 3) * 255
        im = Image.fromarray(imarray.astype('uint8')).convert('RGB')
        im.save(os.path.join(tmp_dir, f'{i}.jpg'))
    yield tmp_dir


@pytest.fixture
def averager():
    yield utils.Averager()


@pytest.fixture
def empty_queue():
    yield mptools.MPQueue()


@pytest.fixture
def img_queue(tmp_img_dir, empty_queue):





