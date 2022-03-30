import pytest
from context import utils

@pytest.mark.parametrize('curr_time,max_sleep,end_time,expected_time',
                         [(10, 10, 100, 10),
                          (90, 20, 100, 10),
                          (100, 10, 90, 0),
                          (100, 10, 100, 0)])

def test_max_sleep(mocker, curr_time, max_sleep, end_time, expected_time):
    mocker.patch('context.utils.time.time', return_value=curr_time)
    assert utils.sleep_secs(max_sleep, end_time) == expected_time

