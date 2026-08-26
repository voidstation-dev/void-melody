import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.tts_job import TTSJobModel
from app.services.job_recovery import recover_jobs
from app.services.tts_service import claim_job


@pytest.mark.asyncio
async def test_claim_job_is_atomic_across_sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'claim.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        job = TTSJobModel(
            text="hello",
            text_hash="atomic-claim",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
        )
        session.add(job)
        await session.commit()
        job_id = job.id

    async def attempt_claim():
        async with session_factory() as session:
            return await claim_job(session, job_id)

    try:
        results = await asyncio.gather(attempt_claim(), attempt_claim())
        assert sorted(results) == [False, True]
        async with session_factory() as session:
            reloaded = await session.get(TTSJobModel, job_id)
            assert reloaded is not None
            assert reloaded.status == "processing"
            assert reloaded.attempt_count == 1
            assert reloaded.started_at is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_recovery_requeues_recoverable_jobs_and_fails_exhausted_jobs(
    async_session_factory,
):
    jobs = [
        TTSJobModel(
            text="processing",
            text_hash="processing",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="processing",
            progress=45,
            attempt_count=1,
        ),
        TTSJobModel(
            text="queued",
            text_hash="queued",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="queued",
            progress=0,
            attempt_count=0,
        ),
        TTSJobModel(
            text="exhausted",
            text_hash="exhausted",
            voice_type="voice",
            voice_display_name="Voice",
            language_code="vi-VN",
            status="processing",
            progress=80,
            attempt_count=3,
        ),
        TTSJobModel(
            text="omnivoice",
            text_hash="omnivoice",
            voice_type="omni-voice",
            voice_display_name="Omni voice",
            language_code="vi-VN",
            provider_id="omnivoice",
            status="queued",
            progress=0,
            attempt_count=0,
        ),
    ]
    async with async_session_factory() as session:
        session.add_all(jobs)
        await session.commit()
        recoverable_ids = {(jobs[0].id, 0), (jobs[1].id, 0), (jobs[3].id, 0)}
        omnivoice_id = jobs[3].id
        exhausted_id = jobs[2].id

    recovered = await recover_jobs(
        session_factory=async_session_factory,
        max_total_attempts=3,
    )

    assert set(recovered) == recoverable_ids
    assert next(item for item in recovered if item.job_id == omnivoice_id).provider_id == "omnivoice"
    async with async_session_factory() as session:
        recovered_jobs = [
            await session.get(TTSJobModel, job_id) for job_id, _ in recovered
        ]
        assert all(job is not None and job.status == "queued" for job in recovered_jobs)
        assert all(job is not None and job.progress == 0 for job in recovered_jobs)
        exhausted = await session.get(TTSJobModel, exhausted_id)
        assert exhausted is not None
        assert exhausted.status == "failed"
        assert exhausted.error_code == "WORKER_INTERRUPTED"
