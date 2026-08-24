"""Batch Repository for database operations on TTS batches."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tts_batch import TTSBatchModel


class BatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, batch_id: str) -> TTSBatchModel | None:
        return await self.session.get(TTSBatchModel, batch_id)

    async def list_batches(self, limit: int = 50) -> Sequence[TTSBatchModel]:
        stmt = select(TTSBatchModel).order_by(desc(TTSBatchModel.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def save(self, batch: TTSBatchModel) -> TTSBatchModel:
        self.session.add(batch)
        await self.session.commit()
        return batch
