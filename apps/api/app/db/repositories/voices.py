"""Custom Voice Repository for database operations on cloned voices."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_voice import CustomVoiceModel


class CustomVoiceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, voice_id: str) -> CustomVoiceModel | None:
        return await self.session.get(CustomVoiceModel, voice_id)

    async def list_voices(self, status: str | None = None) -> Sequence[CustomVoiceModel]:
        stmt = select(CustomVoiceModel)
        if status:
            stmt = stmt.where(CustomVoiceModel.status == status)
        stmt = stmt.order_by(desc(CustomVoiceModel.created_at))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def save(self, voice: CustomVoiceModel) -> CustomVoiceModel:
        self.session.add(voice)
        await self.session.commit()
        return voice
