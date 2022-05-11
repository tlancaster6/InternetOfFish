from context import runner, detector, mptools, metadata
import pytest

# @pytest.fixture
# def mock_metadata():
#     mm = metadata.MetaDataDict()
#     mm.quick_update({'owner': 'foo',
#                      'species': 'bar',
#                      'fish_type': 'other',
#                      'model_id': 'efficientdet_april25',
#                      })
#     yield mm.simplify()
#
# @pytest.fixture
# def testing_context(mock_metadata):
#     yield mptools.MainContext(mock_metadata)

def test_runner_subproc_mocks(mocker):
    mocker.patch('context.detector.HitCounter')
    assert type(detector.HitCounter()) is mocker.MagicMock
