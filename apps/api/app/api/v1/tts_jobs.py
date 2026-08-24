import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.models.tts_job import TTSJobModel
from app.schemas.tts import (
    BatchJobCreateResponse,
    CreateTTSBatchJobsRequest,
    CreateTTSJobRequest,
    TTSJobListResponse,
    TTSJobResponse,
    TTSPreviewRequest,
)
from app.services.tts_service import (
    create_tts_job,
    create_tts_job_with_batch_limits,
    create_tts_jobs_batch,
    get_job_by_id,
    list_jobs,
)
from app.services.voice_catalog import voice_catalog
from app.services.voice_resolver import VoiceResolutionError, resolve_voice
from app.utils.text_utils import slugify_vietnamese

router = APIRouter()
logger = logging.getLogger(__name__)


def serialize_job(job: TTSJobModel) -> TTSJobResponse:
    text_prev = job.text[:80] + "..." if len(job.text) > 80 else job.text
    return TTSJobResponse(
        id=job.id,
        text=job.text,
        textPreview=text_prev,
        voiceType=job.voice_type,
        voiceDisplayName=job.voice_display_name,
        resourceId=job.resource_id,
        rate=job.rate,
        providerId=job.provider_id,
        status=job.status,
        progress=job.progress,
        batchId=job.batch_id,
        batchPosition=job.batch_position,
        style=job.style,
        sourceFileName=job.source_file_name,
        sourceFileSize=job.source_file_size,
        audioUrl=f"/api/v1/tts/jobs/{job.id}/audio"
        if job.status == "completed"
        else None,
        audioDuration=job.audio_duration,
        downloadUrl=f"/api/v1/tts/jobs/{job.id}/download"
        if job.status == "completed"
        else None,
        fileSize=job.audio_file_size,
        errorCode=job.error_code,
        errorMessage=job.error_message,
        createdAt=job.created_at.isoformat(),
        startedAt=job.started_at.isoformat() if job.started_at else None,
        updatedAt=job.updated_at.isoformat(),
        completedAt=job.completed_at.isoformat() if job.completed_at else None,
    )


from app.workers.queue_manager import queue_manager


@router.post(
    "/tts/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchJobCreateResponse,
)
async def create_job_endpoint(
    req: CreateTTSJobRequest,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008,
):
    if len(req.text) > settings.tts_max_text_chars:
        raise HTTPException(status_code=422, detail="TEXT_TOO_LONG")

    try:
        matched = await resolve_voice(session, req.voiceType)
    except VoiceResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{exc.code}: {exc.message}",
        ) from exc

    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided")

    batch_id = req.batchId if req.batchId else str(uuid.uuid4())
    batch_position = req.batchPosition if req.batchPosition is not None else 0

    create_job = create_tts_job_with_batch_limits if req.batchId else create_tts_job
    create_kwargs = {
        "text": req.text,
        "voice_type": req.voiceType,
        "voice_display_name": matched.display_name,
        "language_code": matched.language_code,
        "resource_id": matched.resource_id,
        "rate": req.rate,
        "batch_id": batch_id,
        "batch_position": batch_position,
        "style": req.style,
        "provider_id": getattr(matched, "provider_id", "capcut"),
        "source_file_name": req.sourceFileName,
        "source_file_size": req.sourceFileSize,
        "export_path": req.exportPath,
        "export_format": req.exportFormat,
    }
    if req.batchId:
        create_kwargs.update(
            max_files=settings.tts_max_batch_files,
            max_total_chars=settings.tts_max_batch_total_chars,
        )
    job = await create_job(session, **create_kwargs)

    await queue_manager.enqueue(job.id, batch_position=job.batch_position or 0)

    return BatchJobCreateResponse(batchId=batch_id, jobs=[serialize_job(job)])


@router.post(
    "/tts/jobs/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchJobCreateResponse,
)
async def create_batch_jobs_endpoint(
    req: CreateTTSBatchJobsRequest,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008,
):
    if not req.items:
        raise HTTPException(status_code=400, detail="No items provided in batch request")

    batch_id = str(uuid.uuid4())
    job_items_data = []

    for i, item in enumerate(req.items):
        if not item.text.strip():
            continue
        if len(item.text) > settings.tts_max_text_chars:
            raise HTTPException(status_code=422, detail="TEXT_TOO_LONG")
        try:
            matched = await resolve_voice(session, item.voiceType)
        except VoiceResolutionError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"{exc.code}: {exc.message}",
            ) from exc

        job_items_data.append({
            "text": item.text,
            "voice_type": item.voiceType,
            "voice_display_name": matched.display_name,
            "language_code": matched.language_code,
            "resource_id": matched.resource_id,
            "rate": item.rate,
            "batch_position": i,
            "style": item.style,
            "provider_id": getattr(matched, "provider_id", "capcut"),
            "source_file_name": item.sourceFileName,
            "source_file_size": item.sourceFileSize,
            "export_path": item.exportPath,
            "export_format": item.exportFormat,
        })

    if not job_items_data:
        raise HTTPException(status_code=400, detail="No valid jobs could be created from the batch.")

    created_jobs = await create_tts_jobs_batch(
        session,
        batch_id=batch_id,
        items=job_items_data,
        max_files=settings.tts_max_batch_files,
        max_total_chars=settings.tts_max_batch_total_chars,
    )

    for job in created_jobs:
        await queue_manager.enqueue(job.id, batch_position=job.batch_position or 0)

    return BatchJobCreateResponse(batchId=batch_id, jobs=[serialize_job(j) for j in created_jobs])


from pydantic import BaseModel

class ExportJobRequest(BaseModel):
    exportPath: str
    exportFormat: str = "mp3"

@router.post("/tts/jobs/{job_id}/export")
async def export_job_endpoint(
    job_id: str,
    req: ExportJobRequest,
    session: AsyncSession = Depends(get_async_session),
):
    job = await get_job_by_id(session, job_id)
    if not job or job.status != "completed" or not job.audio_path:
        raise HTTPException(status_code=404, detail="AUDIO_NOT_READY")

    try:
        import shutil
        import asyncio
        from pathlib import Path
        
        export_file = Path(req.exportPath)
        export_file.parent.mkdir(parents=True, exist_ok=True)

        if req.exportFormat not in {"mp3", "m4a", "wav"}:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        if req.exportFormat == "mp3":
            await asyncio.to_thread(shutil.copy2, job.audio_path, export_file)
        elif req.exportFormat == "wav":
            await convert_mp3_to_wav(job.audio_path, str(export_file))
        else:
            ffmpeg_binary = settings.ffmpeg_binary_path
            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                str(job.audio_path),
                "-c:a",
                "aac",
                "-b:a",
                "256k",
                str(export_file),
            ]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise HTTPException(status_code=500, detail=f"Export failed: {stderr}")

        return {"status": "success", "path": str(export_file)}
    except Exception as e:
        logger.error(f"Failed to export job {job_id} to {req.exportPath}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/tts/jobs", response_model=TTSJobListResponse)
async def list_jobs_endpoint(
    status: str | None = None,
    page: int = 1,
    pageSize: int = 20,
    cursor: str | None = None,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008,
):
    jobs, total, next_cursor = await list_jobs(
        session, status=status, page=page, page_size=pageSize, cursor=cursor
    )
    return TTSJobListResponse(
        items=[serialize_job(j) for j in jobs],
        page=page,
        pageSize=pageSize,
        total=total,
        nextCursor=next_cursor,
    )


@router.get("/tts/jobs/{job_id}", response_model=TTSJobResponse)
async def get_job_endpoint(
    job_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    job = await get_job_by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
    return serialize_job(job)


import os

from app.utils.audio_utils import convert_mp3_to_m4a, convert_mp3_to_wav


@router.get("/tts/jobs/{job_id}/audio")
async def stream_audio_endpoint(
    job_id: str,
    format: str = "mp3",
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    job = await get_job_by_id(session, job_id)
    if not job or job.status != "completed" or not job.audio_path:
        raise HTTPException(status_code=404, detail="AUDIO_NOT_READY")

    file_path = job.audio_path
    media_type = "audio/mpeg"

    if format == "m4a":
        m4a_path = job.audio_path.replace(".mp3", ".m4a")
        await convert_mp3_to_m4a(job.audio_path, m4a_path)
        file_path = m4a_path
        media_type = "audio/mp4"
    elif format == "wav":
        wav_path = job.audio_path.replace(".mp3", ".wav")
        await convert_mp3_to_wav(job.audio_path, wav_path)
        file_path = wav_path
        media_type = "audio/wav"

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
    }

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=f"capvoice-{job.id}.{format}",
        headers=headers,
    )


@router.get("/tts/jobs/{job_id}/download")
async def download_audio_endpoint(
    job_id: str,
    format: str = "mp3",
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    job = await get_job_by_id(session, job_id)
    if not job or job.status != "completed" or not job.audio_path:
        raise HTTPException(status_code=404, detail="AUDIO_NOT_READY")

    file_path = job.audio_path
    media_type = "audio/mpeg"

    if format == "m4a":
        m4a_path = job.audio_path.replace(".mp3", ".m4a")
        await convert_mp3_to_m4a(job.audio_path, m4a_path)
        file_path = m4a_path
        media_type = "audio/mp4"
    elif format == "wav":
        wav_path = job.audio_path.replace(".mp3", ".wav")
        await convert_mp3_to_wav(job.audio_path, wav_path)
        file_path = wav_path
        media_type = "audio/wav"

    slug = slugify_vietnamese(job.text)
    filename = f"{slug}.{format}"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
    }

    return FileResponse(
        path=file_path, media_type=media_type, filename=filename, headers=headers
    )


@router.delete("/tts/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_endpoint(
    job_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    job = await get_job_by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")

    # Optional: Delete associated audio files
    if job.audio_path and os.path.exists(job.audio_path):
        try:
            os.remove(job.audio_path)
            # Delete m4a if exists
            m4a_path = job.audio_path.replace(".mp3", ".m4a")
            if os.path.exists(m4a_path):
                os.remove(m4a_path)
        except Exception:
            logger.exception(
                "Failed deleting audio files",
                extra={"job_id": job.id},
            )

    await session.delete(job)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/tts/jobs/{job_id}/retry", response_model=TTSJobResponse)
async def retry_job_endpoint(
    job_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    job = await get_job_by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")

    if job.status not in ["failed", "completed"]:
        raise HTTPException(
            status_code=400, detail="Only failed or completed jobs can be retried"
        )

    retry_kwargs = {
        "text": job.text,
        "voice_type": job.voice_type,
        "voice_display_name": job.voice_display_name,
        "language_code": job.language_code,
        "resource_id": job.resource_id,
        "rate": job.rate,
        "kind": job.kind,
        "batch_id": job.batch_id,
        "batch_position": job.batch_position,
        "source_file_name": job.source_file_name,
        "source_file_size": job.source_file_size,
        "provider_id": job.provider_id,
        "backbone_id": job.backbone_id,
        "style": job.style,
        "voice_profile_id": job.voice_profile_id,
        "request_metadata": job.request_metadata,
    }
    if job.batch_id:
        retried_job = await create_tts_job_with_batch_limits(
            session,
            **retry_kwargs,
            max_files=settings.tts_max_batch_files,
            max_total_chars=settings.tts_max_batch_total_chars,
        )
    else:
        retried_job = await create_tts_job(session, **retry_kwargs)
    await queue_manager.enqueue(retried_job.id, batch_position=retried_job.batch_position or 0)

    return serialize_job(retried_job)


from fastapi.responses import StreamingResponse

@router.post("/tts/preview")
async def preview_tts_endpoint(
    req: TTSPreviewRequest,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    if len(req.text) > 1000:
        raise HTTPException(status_code=422, detail="Text too long for preview")

    try:
        matched = await resolve_voice(session, req.voiceType)
    except VoiceResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{exc.code}: {exc.message}",
        ) from exc

    provider = queue_manager.provider_registry.get(matched.provider_id)
    if provider is None:
        raise HTTPException(status_code=422, detail="PROVIDER_NOT_FOUND")

    # We return a StreamingResponse that yields bytes
    async def generator():
        try:
            async for chunk in provider.synthesize_stream(
                text=req.text,
                voice_type=req.voiceType,
                resource_id=matched.resource_id,
                rate=req.rate,
                style=req.style,
            ):
                yield chunk
        except Exception as e:  # noqa: BLE001
            logger.error("Error streaming preview: %s", e)

    return StreamingResponse(generator(), media_type="audio/mpeg")


@router.post("/tts/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_job_endpoint(
    job_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    job = await get_job_by_id(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")

    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400, detail="Job cannot be cancelled in its current state"
        )

    from app.scheduler.cancellation import cancellation_registry

    if job.status == "queued":
        job.status = "cancelled"
    else:
        # If processing, signal cancellation
        job.cancel_requested = True

    await cancellation_registry.cancel(job_id)
    await session.commit()
    return serialize_job(job)
