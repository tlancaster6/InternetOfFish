import os, shutil
import pytest
from context import RESOURCES_DIR, MODEL_DIR, TMP_DIR, Detector, HitCounter
import pycoral

@pytest.fixture
def setup_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)
    yield
    shutil.rmtree(TMP_DIR)

@pytest.fixture
def detector(setup_tmp_dir):
    model_path = os.path.join(MODEL_DIR, 'test_model.tflite')
    label_path = os.path.join(MODEL_DIR, 'labels.txt')
    d = Detector(model_path, label_path)
    return d

@pytest.fixture
def hit_counter():
    return HitCounter()


def test_hit_counter(hit_counter):
    hit_counter.increment()
    assert hit_counter.hits == 1
    hit_counter.increment()
    assert hit_counter.hits == 2
    hit_counter.decrement()
    assert hit_counter.hits == 1
    hit_counter.decrement()
    assert hit_counter.hits == 0
    hit_counter.decrement()
    assert hit_counter.hits == 0


def test_detect(detector):
    img_path = os.path.join(RESOURCES_DIR, 'test_images', 'demasoni.jpg')
    dets = detector.detect(img_path)
    assert type(dets) is list
    assert type(dets[0]) is pycoral.adapters.detect.Object
