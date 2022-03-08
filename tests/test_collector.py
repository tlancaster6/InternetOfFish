import os, shutil
import pytest
from .context import TEST_DATA_DIR, TMP_DIR, Collector, generate_vid_id

@pytest.fixture
def setup_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)
    yield
    shutil.rmtree(TMP_DIR)

@pytest.fixture
def collector(setup_tmp_dir):
    vid_dir = os.path.join(TMP_DIR, 'videos')
    img_dir = os.path.join(TMP_DIR, 'images')
    c = Collector(vid_dir, img_dir)
    c.definitions.testing = True
    return c


def test_generate_vid_id(setup_tmp_dir):
    errors = []
    id_0 = generate_vid_id(TMP_DIR)
    if id_0 != '0001_vid':
        errors.append(f'expected vid id to be 0001_vid, got {id_0}')
    f = open(os.path.join(TMP_DIR, '0001_vid.mp4'))
    f.close()
    id_1 = generate_vid_id(TMP_DIR)
    if id_1 != '0002_vid':
        errors.append(f'expected vid id to be 0002_vid, got {id_1}')
    assert not errors, "errors occured:\n{}".format("\n".join(errors))

def test_collector(collector):
    collector.collect_data()
    errors = []
    if '0001_vid.h264' not in os.listdir(collector.vid_dir):
        errors.append(f'expected 0001_vid.h264 in {collector.vid_dir}. found {os.listdir(collector.vid_dir)}')
    image_files = [f for f in os.listdir(collector.img_dir) if f.endswith('.jpg')]
    if len(image_files) != 100:
        errors.append(f'expected 100 images in {collector.img_dir}, found {len(image_files)}')
    assert not errors, "errors occured:\n{}".format("\n".join(errors))





