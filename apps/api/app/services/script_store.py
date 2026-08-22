"""Persistence helpers for script documents and revision-safe autosave."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emotional_script import EmotionalScriptModel
from app.schemas.emotional_script import EmotionalScriptDocument


class ScriptNotFound(LookupError):
    pass


class ScriptRevisionConflict(RuntimeError):
    pass


def _document_for_row(document: EmotionalScriptDocument, *, script_id: str, revision: int) -> str:
    normalized = document.model_copy(update={"id": script_id, "revision": revision})
    return json.dumps(normalized.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)


def document_from_row(row: EmotionalScriptModel) -> EmotionalScriptDocument:
    return EmotionalScriptDocument.model_validate(json.loads(row.document_json))


async def create_script(
    session: AsyncSession,
    document: EmotionalScriptDocument,
    *,
    title: str | None = None,
) -> EmotionalScriptModel:
    row = EmotionalScriptModel(
        title=(title or document.title).strip() or "Kịch bản chưa đặt tên",
        document_json="",
        schema_version=document.version,
        revision=1,
    )
    session.add(row)
    await session.flush()
    row.document_json = _document_for_row(document, script_id=row.id, revision=1)
    await session.commit()
    await session.refresh(row)
    return row


async def get_script(session: AsyncSession, script_id: str) -> EmotionalScriptModel:
    row = await session.get(EmotionalScriptModel, script_id)
    if row is None:
        raise ScriptNotFound(script_id)
    return row


async def update_script(
    session: AsyncSession,
    script_id: str,
    document: EmotionalScriptDocument,
    *,
    expected_revision: int,
) -> EmotionalScriptModel:
    row = await get_script(session, script_id)
    if row.revision != expected_revision:
        raise ScriptRevisionConflict(
            f"Script {script_id} is at revision {row.revision}; expected {expected_revision}."
        )
    row.revision += 1
    row.title = document.title.strip() or row.title
    row.schema_version = document.version
    row.document_json = _document_for_row(document, script_id=script_id, revision=row.revision)
    await session.commit()
    await session.refresh(row)
    return row


async def list_scripts(session: AsyncSession) -> list[EmotionalScriptModel]:
    result = await session.execute(
        select(EmotionalScriptModel).order_by(EmotionalScriptModel.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_script(session: AsyncSession, script_id: str) -> None:
    row = await get_script(session, script_id)
    await session.delete(row)
    await session.commit()

