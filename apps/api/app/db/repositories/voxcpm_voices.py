"""VoxCPM2 voice repository for database operations on cloned voices."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voxcpm_voice import VoxCpmVoiceModel


class VoxCpmVoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, voice_id: str) -> VoxCpmVoiceModel | None:
        return await self.session.get(VoxCpmVoiceModel, voice_id)

    async def list_voices(
        self,
        status: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[VoxCpmVoiceModel]:
        stmt = select(VoxCpmVoiceModel)
        count_stmt = select(func.count(VoxCpmVoiceModel.id))
        if status:
            stmt = stmt.where(VoxCpmVoiceModel.status == status)
            count_stmt = count_stmt.where(VoxCpmVoiceModel.status == status)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(VoxCpmVoiceModel.display_name.ilike(pattern))
            count_stmt = count_stmt.where(VoxCpmVoiceModel.display_name.ilike(pattern))
        stmt = stmt.order_by(desc(VoxCpmVoiceModel.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        self.last_total = await self.session.scalar(count_stmt)
        return result.scalars().all()

    async def save(self, voice: VoxCpmVoiceModel) -> VoxCpmVoiceModel:
        self.session.add(voice)
        await self.session.commit()
        return voice

    async def delete(self, voice: VoxCpmVoiceModel) -> None:
        await self.session.delete(voice)
        await self.session.commit()