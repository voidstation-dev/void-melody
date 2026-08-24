"""TTS Job Repository for database operations on TTS jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tts_job import TTSJobModel


class TTSJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, job_id: str) -> TTSJobModel | None:
        return await self.session.get(TTSJobModel, job_id)

    async def count_active_jobs(self) -> int:
        result = await self.session.execute(
            select(func.count(TTSJobModel.id)).where(
                TTSJobModel.status.in_(["queued", "processing"])
            )
        )
        return int(result.scalar_one())

    async def list_jobs(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
        batch_id: str | None = None,
        before_created_at: datetime | None = None,
        before_id: str | None = None,
    ) -> Sequence[TTSJobModel]:
        stmt = select(TTSJobModel)
        if status:
            stmt = stmt.where(TTSJobModel.status == status)
        if batch_id:
            stmt = stmt.where(TTSJobModel.batch_id == batch_id)
        if before_created_at is not None:
            if before_id is not None:
                stmt = stmt.where(
                    (TTSJobModel.created_at < before_created_at)
                    | (
                        (TTSJobModel.created_at == before_created_at)
                        & (TTSJobModel.id < before_id)
                    )
                )
            else:
                stmt = stmt.where(TTSJobModel.created_at < before_created_at)

        stmt = stmt.order_by(desc(TTSJobModel.created_at), desc(TTSJobModel.id)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def save_batch(self, jobs: Sequence[TTSJobModel]) -> Sequence[TTSJobModel]:
        self.session.add_all(jobs)
        await self.session.commit()
        return jobs
