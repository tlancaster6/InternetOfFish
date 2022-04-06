import os.path
import pytest
import datetime
import logging
import shutil
from numpy.random import rand

import internet_of_fish.modules.advanced_utils
from context import utils, definitions
from PIL import Image

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


@pytest.mark.parametrize('curr_time,max_sleep,end_time,expected_time',
                         [(10, 10, 100, 10),
                          (90, 20, 100, 10),
                          (100, 10, 90, 0),
                          (100, 10, 100, 0)])
def test_max_sleep(mocker, curr_time, max_sleep, end_time, expected_time):
    mocker.patch('context.utils.time.time', return_value=curr_time)
    assert utils.sleep_secs(max_sleep, end_time) == expected_time


def test_current_time_ms(mocker):
    mocker.patch('context.utils.time.time', return_value=100)
    assert utils.current_time_ms() == 100000


def test_current_time_iso(mocker):
    mock_val = datetime.datetime(2000, 1, 1, 12, 0, 0, 10)
    mock_datetime = mocker.patch('context.utils.datetime.datetime')
    mock_datetime.now.return_value = mock_val
    assert utils.current_time_iso() == '2000-01-01T12:00:00'


def test_make_logger_return_type(mocker):
    mocker.patch('context.utils.os.path.exists', return_value = False)
    assert type(utils.make_logger('test')) == logging.Logger


@pytest.mark.parametrize('t,lof', [(definitions.START_HOUR-1, False),
                                   (definitions.END_HOUR+1, False),
                                   (definitions.START_HOUR, True),
                                   (definitions.END_HOUR, False)])
def test_lights_on(t, lof):
    t = datetime.datetime(2000, 1, 1, t, 0, 0)
    assert utils.lights_on(t) == lof


@pytest.mark.parametrize('curr_time,expected_time',
                         [(datetime.datetime(2000, 1, 1, 12, 0, 0), 0),
                          (datetime.datetime(2000, 1, 1, definitions.START_HOUR - 1, 59, 59), 1),
                          (datetime.datetime(2000, 1, 1, definitions.END_HOUR, 1, 0), 600),
                          ])
def test_sleep_until_morning(mocker, curr_time, expected_time):
    lof = utils.lights_on(curr_time)
    mocker.patch('context.utils.lights_on', return_value=lof)
    mocker.patch('context.utils.time.time', return_value=datetime.datetime.timestamp(curr_time))
    mock_datetime = mocker.patch('context.utils.datetime.datetime')
    mock_datetime.now.return_value = curr_time
    assert utils.sleep_until_morning() == expected_time


def test_jpgs_to_mp4(tmp_img_dir):
    vid_dir = internet_of_fish.modules.advanced_utils.jpgs_to_mp4(tmp_img_dir, tmp_img_dir)
    assert os.path.exists(vid_dir)


def test_averager_init():
    averager = utils.Averager()
    assert (averager.count == 0) and (averager.avg is None)


@pytest.mark.parametrize('update_vals', [([0]), ([0, 1]), ([0, 1, 2]), ([0.36, 12, -10])])
def test_averager_update(update_vals):
    averager = utils.Averager()
    for val in update_vals:
        averager.update(val)
    assert averager.count == len(update_vals)
    assert averager.avg == sum(update_vals) / len(update_vals)

