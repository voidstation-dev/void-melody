import base64
import hashlib
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tts_job import TTSJobModel, utc_now


def compute_text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


async def claim_job(session: AsyncSession, job_id: str) -> bool:
    result = await session.execute(
        update(TTSJobModel)
        .where(
            TTSJobModel.id == job_id,
            TTSJobModel.status == "queued",
            TTSJobModel.cancel_requested.is_(False),
            TTSJobModel.attempt_count < settings.tts_max_auto_retries + 1,
        )
        .values(
            status="processing",
            progress=0,
            started_at=utc_now(),
            attempt_count=TTSJobModel.attempt_count + 1,
        )
    )
    await session.commit()
    return result.rowcount == 1


async def assert_batch_capacity(
    session: AsyncSession,
    *,
    batch_id: str,
    new_text_length: int,
    max_files: int,
    max_total_chars: int,
    new_items_count: int = 1,
) -> None:
    result = await session.execute(
        select(
            func.count(TTSJobModel.id),
            func.coalesce(func.sum(func.length(TTSJobModel.text)), 0),
        ).where(TTSJobModel.batch_id == batch_id)
    )
    file_count, total_chars = result.one()

    if file_count + new_items_count > max_files:
        raise HTTPException(
            status_code=422,
            detail="BATCH_FILE_LIMIT_EXCEEDED",
        )
    if int(total_chars) + new_text_length > max_total_chars:
        raise HTTPException(
            status_code=422,
            detail="BATCH_TEXT_LIMIT_EXCEEDED",
        )


def _build_tts_job(
    *,
    text: str,
    voice_type: str,
    voice_display_name: str,
    language_code: str,
    resource_id: str | None = None,
    rate: float = 1.0,
    kind: str = "generation",
    batch_id: str | None = None,
    batch_position: int | None = None,
    source_file_name: str | None = None,
    source_file_size: int | None = None,
    provider_id: str = "capcut",
    backbone_id: str | None = None,
    style: str | None = None,
    voice_profile_id: str | None = None,
    request_metadata: str | None = None,
    export_path: str | None = None,
    export_format: str | None = None,
    license_entitlement_id: str | None = None,
) -> TTSJobModel:
    cleaned_text = text.strip()
    return TTSJobModel(
        kind=kind,
        text=cleaned_text,
        text_hash=compute_text_hash(cleaned_text),
        voice_type=voice_type,
        voice_display_name=voice_display_name,
        resource_id=resource_id,
        language_code=language_code,
        rate=rate,
        status="queued",
        batch_id=batch_id,
        batch_position=batch_position,
        source_file_name=source_file_name,
        source_file_size=source_file_size,
        provider_id=provider_id,
        backbone_id=backbone_id,
        style=style,
        voice_profile_id=voice_profile_id,
        request_metadata=request_metadata,
        export_path=export_path,
        export_format=export_format,
        license_entitlement_id=license_entitlement_id,
    )


async def create_tts_job(
    session: AsyncSession,
    *,
    text: str,
    voice_type: str,
    voice_display_name: str,
    language_code: str,
    resource_id: str | None = None,
    rate: float = 1.0,
    kind: str = "generation",
    batch_id: str | None = None,
    batch_position: int | None = None,
    source_file_name: str | None = None,
    source_file_size: int | None = None,
    provider_id: str = "capcut",
    backbone_id: str | None = None,
    style: str | None = None,
    voice_profile_id: str | None = None,
    request_metadata: str | None = None,
    export_path: str | None = None,
    export_format: str | None = None,
    license_entitlement_id: str | None = None,
) -> TTSJobModel:
    job = _build_tts_job(
        text=text,
        voice_type=voice_type,
        voice_display_name=voice_display_name,
        language_code=language_code,
        resource_id=resource_id,
        rate=rate,
        kind=kind,
        batch_id=batch_id,
        batch_position=batch_position,
        source_file_name=source_file_name,
        source_file_size=source_file_size,
        provider_id=provider_id,
        backbone_id=backbone_id,
        style=style,
        voice_profile_id=voice_profile_id,
        request_metadata=request_metadata,
        export_path=export_path,
        export_format=export_format,
        license_entitlement_id=license_entitlement_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def create_tts_job_with_batch_limits(
    session: AsyncSession,
    *,
    text: str,
    voice_type: str,
    voice_display_name: str,
    language_code: str,
    batch_id: str,
    max_files: int,
    max_total_chars: int,
    resource_id: str | None = None,
    rate: float = 1.0,
    kind: str = "generation",
    batch_position: int | None = None,
    source_file_name: str | None = None,
    source_file_size: int | None = None,
    provider_id: str = "capcut",
    backbone_id: str | None = None,
    style: str | None = None,
    voice_profile_id: str | None = None,
    request_metadata: str | None = None,
    export_path: str | None = None,
    export_format: str | None = None,
    license_entitlement_id: str | None = None,
) -> TTSJobModel:
    try:
        await session.execute(sql_text("BEGIN IMMEDIATE"))
        await assert_batch_capacity(
            session,
            batch_id=batch_id,
            new_text_length=len(text.strip()),
            max_files=max_files,
            max_total_chars=max_total_chars,
        )
        job = _build_tts_job(
            text=text,
            voice_type=voice_type,
            voice_display_name=voice_display_name,
            language_code=language_code,
            resource_id=resource_id,
            rate=rate,
            kind=kind,
            batch_id=batch_id,
            batch_position=batch_position,
            source_file_name=source_file_name,
            source_file_size=source_file_size,
            provider_id=provider_id,
            backbone_id=backbone_id,
            style=style,
            voice_profile_id=voice_profile_id,
            request_metadata=request_metadata,
            export_path=export_path,
            export_format=export_format,
            license_entitlement_id=license_entitlement_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job
    except BaseException:
        await session.rollback()
        raise


async def create_tts_jobs_batch(
    session: AsyncSession,
    *,
    batch_id: str,
    items: list[dict[str, Any]],
    max_files: int = settings.tts_max_batch_files,
    max_total_chars: int = settings.tts_max_batch_total_chars,
    license_entitlement_id: str | None = None,
) -> list[TTSJobModel]:
    """Create all batch jobs in ONE single atomic transaction."""
    if not items:
        return []

    total_new_chars = sum(len(item["text"].strip()) for item in items)
    try:
        await session.execute(sql_text("BEGIN IMMEDIATE"))
        await assert_batch_capacity(
            session,
            batch_id=batch_id,
            new_text_length=total_new_chars,
            max_files=max_files,
            max_total_chars=max_total_chars,
            new_items_count=len(items),
        )

        jobs = [
            _build_tts_job(
                text=item["text"],
                voice_type=item["voice_type"],
                voice_display_name=item.get("voice_display_name", item["voice_type"]),
                language_code=item.get("language_code", "vi-VN"),
                resource_id=item.get("resource_id"),
                rate=item.get("rate", 1.0),
                kind=item.get("kind", "generation"),
                batch_id=batch_id,
                batch_position=item.get("batch_position", idx),
                source_file_name=item.get("source_file_name"),
                source_file_size=item.get("source_file_size"),
                provider_id=item.get("provider_id", "capcut"),
                backbone_id=item.get("backbone_id"),
                style=item.get("style"),
                voice_profile_id=item.get("voice_profile_id"),
                request_metadata=item.get("request_metadata"),
                export_path=item.get("export_path"),
                export_format=item.get("export_format"),
                license_entitlement_id=license_entitlement_id,
            )
            for idx, item in enumerate(items)
        ]

        session.add_all(jobs)
        await session.commit()
        for job in jobs:
            await session.refresh(job)
        return jobs
    except BaseException:
        await session.rollback()
        raise


def encode_cursor(created_at: datetime, job_id: str) -> str:
    raw = f"{created_at.isoformat()}|{job_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str) -> tuple[datetime, str] | None:
    try:
        decoded = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        iso_ts, job_id = decoded.split("|", 1)
        return datetime.fromisoformat(iso_ts), job_id
    except Exception:
        return None


async def get_job_by_id(session: AsyncSession, job_id: str) -> TTSJobModel | None:
    return await session.get(TTSJobModel, job_id)


async def list_jobs(
    session: AsyncSession,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    cursor: str | None = None,
) -> tuple[Sequence[TTSJobModel], int, str | None]:
    """List jobs supporting both cursor-based pagination and classic offset pagination.

    Returns:
        (jobs, total_count, next_cursor)
    """
    stmt = select(TTSJobModel).order_by(
        TTSJobModel.created_at.desc(), TTSJobModel.id.desc()
    )
    if status:
        stmt = stmt.where(TTSJobModel.status == status)

    if cursor:
        cursor_data = decode_cursor(cursor)
        if cursor_data:
            c_time, c_id = cursor_data
            stmt = stmt.where(
                (TTSJobModel.created_at < c_time)
                | ((TTSJobModel.created_at == c_time) & (TTSJobModel.id < c_id))
            )
        # Fetch 1 extra row to determine next cursor without COUNT query
        stmt = stmt.limit(page_size + 1)
        result = (await session.execute(stmt)).scalars().all()
        has_next = len(result) > page_size
        items = result[:page_size]
        next_cursor = (
            encode_cursor(items[-1].created_at, items[-1].id)
            if has_next and items
            else None
        )
        return items, len(items), next_cursor

    # Offset pagination mode
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    jobs = (await session.execute(stmt)).scalars().all()
    next_cursor = (
        encode_cursor(jobs[-1].created_at, jobs[-1].id)
        if jobs and (offset + len(jobs) < total)
        else None
    )

    return jobs, total, next_cursor
