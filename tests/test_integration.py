import time

import pytest
from context import runner, metadata, mptools

@pytest.fixture
def mock_metadata():
    mm = metadata.MetaDataDict()
    mm.quick_update({'owner': 'foo',
                     'species': 'bar',
                     'fish_type': 'other',
                     'model_id': 'efficientdet_april25',
                     })
    yield mm.simplify()

@pytest.fixture
def testing_context(mock_metadata):
    yield mptools.MainContext(mock_metadata)

@pytest.mark.parametrize('mode', ['active', 'passive'])
def test_runner_startup(mocker, testing_context, mode):
    with testing_context as main_ctx:
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        runner_patch = mocker.patch('context.runner.RunnerWorker.return_value.expected_mode', return_value=mode)
        mocker.patch('context.runner.RunnerWorker.return_value.logger.debug', new_callable=print)
        mocker.patch('context.runner.collector.CollectorWorker.return_value')
        mocker.patch('context.runner.detector.DetectorWorker.return_value')
        runner_proc = main_ctx.Proc('RUN', runner.RunnerWorker, main_ctx, persistent=True)
        runner_proc.startup_event.wait(10)
        assert runner_proc.startup_event.is_set()
        assert runner_proc.proc.is_alive()

@pytest.mark.parametrize('mode', ['active', 'passive'])
def test_runner_hard_shutdown(mocker, testing_context, mode):
    with testing_context as main_ctx:
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        mocker.patch('context.runner.RunnerWorker.return_value.expected_mode', return_value=mode)
        mocker.patch('context.runner.RunnerWorker.return_value.logger.debug', new_callable=print)
        mocker.patch('context.runner.collector.CollectorWorker.return_value')
        mocker.patch('context.runner.detector.DetectorWorker.return_value')
        runner_proc = main_ctx.Proc('RUN', runner.RunnerWorker, main_ctx, persistent=True)
        runner_proc.startup_event.wait(10)
        main_ctx.event_queue.safe_put(mptools.EventMessage('test', 'HARD_SHUTDOWN', ''))
        runner_proc.shutdown_event.wait(10)
        assert runner_proc.shutdown_event.is_set()
        assert not main_ctx.procs
        assert not runner_proc.proc.is_alive()

@pytest.mark.parametrize('mode', ['active', 'passive'])
def test_runner_soft_shutdown(mocker, testing_context, mode):
    with testing_context as main_ctx:
        mptools.init_signals(main_ctx.shutdown_event, mptools.default_signal_handler, mptools.default_signal_handler)
        mocker.patch('context.runner.RunnerWorker.return_value.expected_mode', return_value=mode)
        mocker.patch('context.runner.RunnerWorker.return_value.logger.debug', new_callable=print)
        mocker.patch('context.runner.collector.CollectorWorker.return_value')
        mocker.patch('context.runner.detector.DetectorWorker.return_value')
        runner_proc = main_ctx.Proc('RUN', runner.RunnerWorker, main_ctx, persistent=True)
        runner_proc.startup_event.wait(10)
        main_ctx.event_queue.safe_put(mptools.EventMessage('test', 'SOFT_SHUTDOWN', ''))
        time.sleep(10)
        assert not runner_proc.shutdown_event.is_set()
        assert runner_proc.proc.is_alive()
        if mode == 'active':
            assert runner_proc.detector_proc and not runner_proc.detector_proc.proc.is_alive()
            assert runner_proc.collector_proc and not runner_proc.collector_proc.proc.is_alive()
            assert runner_proc.notifier_proc and not runner_proc.notifier_proc.proc.is_alive()
        elif mode == 'passive':
            assert runner_proc.uploader_proc and not runner_proc.uploader_proc.proc.is_alive()
            assert runner_proc.notifier_proc and not runner_proc.notifier_proc.proc.is_alive()





