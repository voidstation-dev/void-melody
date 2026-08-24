"""Audio Cache Repository for database operations on audio segments."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio_cache import AudioSegmentCacheModel


class AudioCacheRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_fingerprint(self, fingerprint: str) -> AudioSegmentCacheModel | None:
        return await self.session.get(AudioSegmentCacheModel, fingerprint)

    async def list_oldest_used(self, limit: int = 100) -> Sequence[AudioSegmentCacheModel]:
        stmt = select(AudioSegmentCacheModel).order_by(AudioSegmentCacheModel.last_used_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_expired(self, older_than: datetime) -> int:
        stmt = delete(AudioSegmentCacheModel).where(AudioSegmentCacheModel.last_used_at < older_than)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)
