import hashlib
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tts_job import TTSJobModel, utc_now
from app.services.trial_service import require_synthesis


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
) -> None:
    result = await session.execute(
        select(
            func.count(TTSJobModel.id),
            func.coalesce(func.sum(func.length(TTSJobModel.text)), 0),
        ).where(TTSJobModel.batch_id == batch_id)
    )
    file_count, total_chars = result.one()

    if file_count + 1 > max_files:
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
) -> TTSJobModel:
    require_synthesis()
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
) -> TTSJobModel:
    require_synthesis()
    try:
        # SQLite has no row-level locks. BEGIN IMMEDIATE serializes the
        # aggregate capacity check and insert without blocking queue readers.
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
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job
    except BaseException:
        await session.rollback()
        raise


async def get_job_by_id(session: AsyncSession, job_id: str) -> TTSJobModel | None:
    return await session.get(TTSJobModel, job_id)


async def list_jobs(
    session: AsyncSession,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[Sequence[TTSJobModel], int]:
    stmt = select(TTSJobModel).order_by(TTSJobModel.created_at.desc())
    if status:
        stmt = stmt.where(TTSJobModel.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    jobs = (await session.execute(stmt)).scalars().all()

    return jobs, total
