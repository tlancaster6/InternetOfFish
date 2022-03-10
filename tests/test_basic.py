import os, shutil, time
import multiprocessing as mp

import pytest
from .context import RESOURCES_DIR, MODEL_DIR, Collector, generate_vid_id, Detector, HitCounter, Manager

@pytest.fixture
def manager():
    m = Manager('test', 'test_model')
    yield m
    shutil.rmtree(m.img_dir)
    shutil.rmtree(m.vid_dir)

@pytest.fixture
def collector(manager):
    return manager.collector

@pytest.fixture
def detector(manager):
    return manager.detector

@pytest.fixture
def hit_counter(manager):
    return manager.detector.hit_counter


def test_locate_model_files(manager):
    model_path, label_path = manager.locate_model_files('test_model')
    model_path = os.path.split(model_path)[-1]
    label_path = os.path.split(label_path)[-1]
    errors = []
    if model_path != 'test_model.tflite':
        errors.append(f'expected test_model.tflite, got {model_path}')
    if label_path != 'labels.txt':
        errors.append(f'expected labels.txt, got {label_path}')
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_generate_vid_id(collector):
    errors = []
    id_0 = generate_vid_id(collector.vid_dir)
    if id_0 != '0001_vid':
        errors.append(f'expected vid id to be 0001_vid, got {id_0}')
    f = open(os.path.join(collector.vid_dir, '0001_vid.mp4'), 'w+')
    f.close()
    id_1 = generate_vid_id(collector.vid_dir)
    if id_1 != '0002_vid':
        errors.append(f'expected vid id to be 0002_vid, got {id_1}')
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


def test_collector(manager):
    errors = []
    collector = manager.collector
    manager.start_collection()
    time.sleep(10)
    manager.stop_collection()
    if '0001_vid.h264' not in os.listdir(collector.vid_dir):
        errors.append(f'expected 0001_vid.h264 in {collector.vid_dir}. found {os.listdir(collector.vid_dir)}')
    image_files = [f for f in os.listdir(collector.img_dir) if f.endswith('.jpg')]
    expected_n =  manager.collector.definitions.WAIT_TIME * 10
    if abs(len(image_files) - expected_n) > 1:
        errors.append(f'expected approximately {expected_n} images in {collector.img_dir}, found {len(image_files)}')
    assert not errors, "errors occured:\n{}".format("\n".join(errors))


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

