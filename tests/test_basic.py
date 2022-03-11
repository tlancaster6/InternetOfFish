import os, shutil, time
import multiprocessing as mp

import pytest
from .context import Manager


@pytest.fixture(scope='session')
def manager():
    m = Manager('test', 'mobilenetv2')
    m.collect_and_detect(iterlimit=1)
    yield m
    shutil.rmtree(m.img_dir)
    shutil.rmtree(m.vid_dir)


def test_all_images_consumed(manager):
    assert manager.img_queue.empty(), f'{manager.img_queue.qsize()}images left in queue'


def test_img_buffer_length(manager):
    n_images_act = len([f.endswith('.jpeg') for f in os.listdir(manager.img_dir)])
    n_images_exp = manager.definitions.IMG_BUFFER
    assert n_images_exp == n_images_act, f'expected {n_images_exp} in buffer, encountered {n_images_act}'


def test_video_created(manager):
    exists = os.path.exists(os.path.join(manager.vid_dir, '0001_vid.h264'))
    assert exists, f'expected 0001_vid.h264 in vid dir, found: {os.listdir(manager.vid_dir)}'


def test_children_cleaned(manager):
    collect_clean = manager.collection_process is None
    detect_clean = manager.detection_process is None
    assert collect_clean and detect_clean, f'expected collect and detect processes to be None' \
                                           f'manager.collection_process = {manager.collection_process}' \
                                           f'manager.detection_process = {manager.detection_process}'


