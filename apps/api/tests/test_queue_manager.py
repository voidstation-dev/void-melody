import asyncio
from unittest.mock import AsyncMock

import pytest

from app.scheduler.policies import ProviderRoutingError
from app.workers.queue_manager import TTSQueueManager


@pytest.mark.asyncio
async def test_queue_manager_starts_only_configured_worker_count():
    manager = TTSQueueManager(concurrency=2)

    await manager.start()
    try:
        assert len(manager.workers) == 2
        assert all(not worker.done() for worker in manager.workers)
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_delayed_enqueue_does_not_block_caller():
    manager = TTSQueueManager(concurrency=1)
    manager.accepting_jobs = True
    started_at = asyncio.get_running_loop().time()

    await manager.enqueue_after("job-1", delay_seconds=0.05)

    assert asyncio.get_running_loop().time() - started_at < 0.02
    assert manager.queue.empty()
    await asyncio.sleep(0.06)
    _, _, job_id = await manager.queue.get()
    assert job_id == "job-1"
    manager.queue.task_done()


@pytest.mark.asyncio
async def test_duplicate_enqueue_is_ignored():
    manager = TTSQueueManager(concurrency=1)
    manager.accepting_jobs = True

    results = await asyncio.gather(
        manager.enqueue("job-1"),
        manager.enqueue("job-1"),
        manager.enqueue("job-1"),
    )

    assert results.count(True) == 1
    assert results.count(False) == 2
    assert manager.queue.qsize() == 1


@pytest.mark.asyncio
async def test_explicit_unknown_provider_does_not_fall_back_to_capcut():
    manager = TTSQueueManager(concurrency=1)
    manager.accepting_jobs = True

    with pytest.raises(ProviderRoutingError) as exc_info:
        await manager.enqueue("job-unknown", provider_id="unknown")

    assert exc_info.value.code == "PROVIDER_LANE_NOT_CONFIGURED"
    assert manager.queue.empty()


@pytest.mark.asyncio
async def test_omitted_provider_keeps_capcut_default():
    manager = TTSQueueManager(concurrency=1)
    manager.accepting_jobs = True

    assert await manager.enqueue("job-default") is True
    _, _, job_id = await manager.queue.get()
    assert job_id == "job-default"
    manager.queue.task_done()


@pytest.mark.asyncio
async def test_queue_workers_share_provider_registry(monkeypatch):

    provider = {"capcut": object()}

    execute = AsyncMock()
    monkeypatch.setattr("app.workers.queue_manager.execute_tts_job_step", execute)
    manager = TTSQueueManager(concurrency=2, provider_registry=provider)

    await manager.start()
    try:
        await manager.enqueue("job-1")
        await manager.enqueue("job-2")
        await asyncio.wait_for(manager.queue.join(), timeout=1)
    finally:
        await manager.stop()

    assert manager.provider_registry == provider
    for call in execute.await_args_list:
        assert call.kwargs["provider_registry"] is provider
    assert len(execute.await_args_list) == 2


@pytest.mark.asyncio
async def test_shutdown_requeues_interrupted_processing_job(monkeypatch):
    started = asyncio.Event()

    async def never_finishes(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    requeue = AsyncMock()
    monkeypatch.setattr(
        "app.workers.queue_manager.execute_tts_job_step",
        never_finishes,
    )
    monkeypatch.setattr(
        "app.workers.queue_manager.requeue_interrupted_job",
        requeue,
        raising=False,
    )
    manager = TTSQueueManager(
        concurrency=1,
        provider_registry={"capcut": object()},
        shutdown_grace_seconds=0.01,
    )

    await manager.start()
    await manager.enqueue("job-1")
    await asyncio.wait_for(started.wait(), timeout=1)
    await manager.stop()

    requeue.assert_awaited_once_with("job-1")
    assert manager.accepting_jobs is False


@pytest.mark.asyncio
async def test_queue_health_snapshot_reports_workers_and_depth():
    manager = TTSQueueManager(concurrency=2, provider_registry={"capcut": object()})
    await manager.start()
    try:
        await manager.enqueue("job-1")
        snapshot = manager.health_snapshot()
        assert snapshot["accepting_jobs"] is True
        assert snapshot["worker_count"] == 2
        assert snapshot["workers_alive"] == 2
        assert snapshot["queue_depth"] in {0, 1}
        assert snapshot["circuit_breaker"]["state"] == "closed"
    finally:
        await manager.stop()
