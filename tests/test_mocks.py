from context import runner, detector, mptools, metadata
import pytest

# @pytest.fixture
# def mock_metadata():
#     mm = metadata.MetaDataDict()
#     mm.quick_update({'owner': 'foo',
#                      'species': 'bar',
#                      'fish_type': 'other',
#                      'model_id': 'efficientdet',
#                      })
#     yield mm.simplify()
#
# @pytest.fixture
# def testing_context(mock_metadata):
#     yield mptools.MainContext(mock_metadata)

def test_runner_subproc_mocks(mocker):
    mocker.patch('detector.HitCounter')
    assert type(detector.HitCounter()) == mocker.MagicMock