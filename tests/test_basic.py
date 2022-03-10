import os, shutil, time
import multiprocessing as mp

import pytest
from .context import Manager

@pytest.fixture
def manager():
    m = Manager('test', 'mobilenetv2')
    yield m
    shutil.rmtree(m.img_dir)
    shutil.rmtree(m.vid_dir)


def test_integration(manager):
    errors = []
    p = mp.Process(target=manager.collect_and_detect)
    p.start()
    time.sleep(20)
    if not manager.collection_process.is_alive():
        errors.append('collection process terminated prematurely')
    if not manager.detection_process.is_alive():
        errors.append('detection process terminated prematurely')
    manager.stop_collection()
    time.sleep(2)
    if manager.collection_process is not None:
        errors.append('collection process failed to terminate')
    manager.stop_detection()
    time.sleep(2)
    if manager.detection_process is not None:
        errors.append('detection process failed to terminate')
    p.join(timeout=10)
    if p.is_alive():
        errors.append('collect_and_detect process failed to terminate')
    collected_imgs = [f.endswith('.jpg') for f in os.listdir(manager.collector.img_dir)]
    collected_vids = [f.endswith('.h264') for f in os.listdir(manager.collector.vid_dir)]
    n_imgs_exp = manager.collector.definitions.IMG_BUFFER
    if len(collected_imgs) != n_imgs_exp:
        errors.append(f'unexpected number of images. expected {n_imgs_exp}, got {len(collected_imgs)}')
    if len(collected_vids) != 1:
        errors.append(f'unexpected number of videos. Expected one, got {len(collected_vids)}')

