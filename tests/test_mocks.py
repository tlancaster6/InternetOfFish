from context import runner, metadata, mptools
import pytest

@pytest.fixture
def mock_metadata():
    mm = metadata.MetaDataDict()
    mm.quick_update({'owner': 'foo',
                     'species': 'bar',
                     'fish_type': 'other',
                     'model_id': 'efficientdet',
                     })
    yield mm.simplify()

@pytest.fixture
def testing_context(mock_metadata):
    yield mptools.MainContext(mock_metadata)

def test_runner_subproc_mocks(mocker, testing_context):
    with testing_context as main_ctx:
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        # mocker.patch('runner.collector.CollectorWorker')
        # mocker.patch('runner.detector.DetectorWorker')
        assert type(runner.collector.CollectorWorker) is mocker.MagicMock