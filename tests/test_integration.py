import time

import pytest
from context import runner, metadata, mptools

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

@pytest.mark.parametrize('mode', ['active', 'passive'])
def test_runner_startup(mocker, testing_context, mode):
    mocker.patch('context.runner')
    with testing_context as main_ctx:
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        mocker.patch('context.runner.RunnerWorker.return_value.expected_mode', return_value=mode)
        runner_proc = main_ctx.Proc('RUN', runner.RunnerWorker, main_ctx, persistent=True)
        runner_proc.startup_event.wait(10)
        assert runner_proc.startup_event.is_set()

@pytest.mark.parametrize('mode', ['active', 'passive'])
def test_runner_shutdown(mocker, testing_context, mode):
    mocker.patch('context.runner')
    with testing_context as main_ctx:
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        mocker.patch('context.runner.RunnerWorker.return_value.expected_mode', return_value=mode)
        runner_proc = main_ctx.Proc('RUN', runner.RunnerWorker, main_ctx, persistent=True)
        runner_proc.startup_event.wait(10)
        runner_proc.shutdown_event.wait(10)
        assert runner_proc.shutdown_event.is_set()





