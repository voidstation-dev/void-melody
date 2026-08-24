"""Comprehensive test suite for VOID_MELODY_BACKEND_OPTIMIZATION_PLAN features."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base
from app.media.cache import compute_segment_fingerprint, lookup_cache, store_cache
from app.media.pipeline import concat_audio_parts
from app.models.audio_cache import AudioSegmentCacheModel
from app.models.tts_job import TTSJobModel
from app.scheduler.cancellation import cancellation_registry
from app.scheduler.lanes import ExecutionLane
from app.scheduler.policies import ProviderExecutionPolicy
from app.scheduler.scheduler import UnifiedScheduler
from app.services.tts_service import create_tts_jobs_batch, list_jobs
from app.services.voice_resolver import invalidate_voice_cache, resolve_voice


@pytest.mark.asyncio
async def test_scheduler_lane_isolation():
    """Verify that a slow VieNeu task does not block CapCut tasks in isolated lanes."""
    capcut_started = []
    vieneu_started = []
    vieneu_blocker = asyncio.Event()

    async def execute_job(job_id: str, worker_id: int):
        if "vieneu" in job_id:
            vieneu_started.append(job_id)
            await vieneu_blocker.wait()
        else:
            capcut_started.append(job_id)

    scheduler = UnifiedScheduler()
    scheduler.lanes["capcut"] = ExecutionLane(
        name="capcut",
        policy=ProviderExecutionPolicy("capcut", 2, 2),
        worker_executor=execute_job,
    )
    scheduler.lanes["vieneu"] = ExecutionLane(
        name="vieneu",
        policy=ProviderExecutionPolicy("vieneu", 1, 1),
        worker_executor=execute_job,
    )

    await scheduler.start()
    try:
        # Enqueue slow vieneu job first
        await scheduler.enqueue("job-vieneu-1", provider_id="vieneu")
        await asyncio.sleep(0.02)
        assert len(vieneu_started) == 1

        # Enqueue multiple capcut jobs
        await scheduler.enqueue("job-capcut-1", provider_id="capcut")
        await scheduler.enqueue("job-capcut-2", provider_id="capcut")
        await asyncio.sleep(0.05)

        # Capcut jobs should have started and completed immediately despite vieneu being blocked
        assert len(capcut_started) == 2
        assert "job-capcut-1" in capcut_started
        assert "job-capcut-2" in capcut_started
    finally:
        vieneu_blocker.set()
        await scheduler.stop()


@pytest.mark.asyncio
async def test_in_memory_cancellation_instant():
    """Verify cancellation registry provides 0ms in-memory cancellation checks."""
    await cancellation_registry.register("job-cancel-test")
    assert cancellation_registry.is_cancelled("job-cancel-test") is False

    await cancellation_registry.cancel("job-cancel-test")
    assert cancellation_registry.is_cancelled("job-cancel-test") is True

    await cancellation_registry.unregister("job-cancel-test")
    assert cancellation_registry.is_cancelled("job-cancel-test") is False


@pytest.mark.asyncio
async def test_audio_segment_cache_lifecycle(tmp_path: Path):
    """Verify storing and looking up cached audio segments."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'cache_test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    source_file = tmp_path / "source.mp3"
    source_file.write_bytes(b"ID3mockaudio")

    fingerprint = compute_segment_fingerprint(
        provider_id="capcut",
        text="Xin chao Viet Nam",
        voice_type="voice_test",
        rate=1.0,
    )

    # 1. Miss initially
    miss = await lookup_cache(fingerprint, session_factory=session_factory)
    assert miss is None

    # 2. Store in cache
    stored = await store_cache(
        fingerprint=fingerprint,
        provider_id="capcut",
        voice_key="voice_test",
        text="Xin chao Viet Nam",
        source_audio_path=source_file,
        session_factory=session_factory,
    )
    assert stored is not None
    assert stored.fingerprint == fingerprint

    # 3. Hit
    hit = await lookup_cache(fingerprint, session_factory=session_factory)
    assert hit is not None
    assert hit.fingerprint == fingerprint
    assert Path(hit.audio_path).is_file()


@pytest.mark.asyncio
async def test_single_transaction_batch_creation(tmp_path: Path):
    """Verify create_tts_jobs_batch creates all jobs atomically with batch positions."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'batch_test.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        created_jobs = await create_tts_jobs_batch(
            session=session,
            items=[
                {"text": "Sentence 1", "voice_type": "bv001", "provider_id": "capcut"},
                {"text": "Sentence 2", "voice_type": "bv001", "provider_id": "capcut"},
                {"text": "Sentence 3", "voice_type": "bv001", "provider_id": "capcut"},
            ],
            batch_id="test-batch-123",
        )
        assert len(created_jobs) == 3
        for idx, job in enumerate(created_jobs):
            assert job.batch_id == "test-batch-123"
            assert job.batch_position == idx
            assert job.status == "queued"

        # Verify cursor pagination
        page1, total, next_cursor = await list_jobs(session, page_size=2)
        assert len(page1) == 2
        assert next_cursor is not None

        page2, _, next_cursor2 = await list_jobs(session, page_size=2, cursor=next_cursor)
        assert len(page2) == 1
        assert page2[0].id not in [j.id for j in page1]
