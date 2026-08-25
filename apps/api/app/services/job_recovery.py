from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.tts_job import TTSJobModel


class RecoveredJob(tuple):
    """2-tuple (job_id, batch_position) subclass that also carries provider_id."""

    job_id: str
    batch_position: int
    provider_id: str

    def __new__(cls, job_id: str, batch_position: int = 0, provider_id: str = "capcut"):
        obj = super().__new__(cls, (job_id, batch_position))
        obj.job_id = job_id
        obj.batch_position = batch_position
        obj.provider_id = provider_id
        return obj

    def __getitem__(self, item):
        if item == 2:
            return self.provider_id
        return super().__getitem__(item)


async def recover_jobs(
    *,
    session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
    max_total_attempts: int | None = None,
) -> list[RecoveredJob]:
    attempt_limit = (
        settings.tts_max_auto_retries + 1
        if max_total_attempts is None
        else max_total_attempts
    )
    async with session_factory() as session:
        result = await session.execute(
            select(TTSJobModel).where(TTSJobModel.status.in_(["queued", "processing"]))
        )
        jobs = result.scalars().all()
        recovered_ids: list[RecoveredJob] = []

        for job in jobs:
            if job.attempt_count >= attempt_limit:
                job.status = "failed"
                job.error_code = "WORKER_INTERRUPTED"
                job.error_message = "The job was interrupted too many times."
                continue

            job.status = "queued"
            job.progress = 0
            job.started_at = None
            job.error_code = None
            job.error_message = None
            recovered_ids.append(RecoveredJob(job.id, job.batch_position or 0, job.provider_id or "capcut"))

        await session.commit()
        return recovered_ids


async def requeue_interrupted_job(
    job_id: str,
    *,
    session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
) -> None:
    async with session_factory() as session:
        await session.execute(
            update(TTSJobModel)
            .where(
                TTSJobModel.id == job_id,
                TTSJobModel.status == "processing",
            )
            .values(
                status="queued",
                progress=0,
                started_at=None,
                error_code=None,
                error_message=None,
            )
        )
        await session.commit()
