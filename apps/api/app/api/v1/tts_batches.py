import asyncio
import os
import tempfile
import uuid
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.models.tts_job import TTSJobModel
from app.schemas.tts import BatchJobCreateResponse, BatchStatusResponse
from app.services.batch_manager import parse_batch_file
from app.services.tts_service import create_tts_jobs_batch
from app.services.voice_catalog import voice_catalog
from app.services.voice_resolver import VoiceResolutionError, resolve_voice
from app.utils.text_utils import slugify_vietnamese
from app.workers.queue_manager import queue_manager

router = APIRouter()

@router.post("/tts/batches", response_model=BatchJobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_batch(
    file: UploadFile = File(...),  # noqa: B008
    voiceType: str = Form(...),
    rate: float = Form(1.0),
    style: str | None = Form(None),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    content = await file.read()
    items = parse_batch_file(file.filename, content)
    
    if not items:
        raise HTTPException(status_code=400, detail="Uploaded file contains no valid text items.")
        
    try:
        matched = await resolve_voice(session, voiceType)
    except VoiceResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{exc.code}: {exc.message}",
        ) from exc
        
    batch_id = str(uuid.uuid4())
    job_items_data = []
    
    from app.api.v1.tts_jobs import serialize_job
    
    for i, text in enumerate(items):
        if len(text) > settings.tts_max_text_chars:
            continue
            
        job_items_data.append({
            "text": text,
            "voice_type": voiceType,
            "voice_display_name": matched.display_name,
            "language_code": matched.language_code,
            "resource_id": matched.resource_id,
            "rate": rate,
            "batch_position": i,
            "style": style,
            "provider_id": getattr(matched, "provider_id", "capcut"),
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


@router.get("/tts/batches/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    stmt = select(TTSJobModel).where(TTSJobModel.batch_id == batch_id).order_by(TTSJobModel.batch_position)
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(status_code=404, detail="BATCH_NOT_FOUND")
        
    total = len(jobs)
    completed = sum(1 for j in jobs if j.status == "completed")
    failed = sum(1 for j in jobs if j.status == "failed")
    pending = sum(1 for j in jobs if j.status in ("queued", "processing"))
    progress = (completed / total) * 100 if total > 0 else 0
    
    from app.api.v1.tts_jobs import serialize_job
    
    return BatchStatusResponse(
        batchId=batch_id,
        totalJobs=total,
        completedJobs=completed,
        failedJobs=failed,
        pendingJobs=pending,
        progress=progress,
        jobs=[serialize_job(j) for j in jobs]
    )


@router.get("/tts/batches/{batch_id}/download")
async def download_batch(
    batch_id: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    stmt = select(TTSJobModel).where(
        TTSJobModel.batch_id == batch_id,
        TTSJobModel.status == "completed"
    )
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    
    if not jobs:
        raise HTTPException(status_code=400, detail="NO_COMPLETED_JOBS_IN_BATCH")
        
    fd, temp_zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    
    def create_zip():
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, job in enumerate(jobs):
                if job.audio_path and os.path.exists(job.audio_path):
                    ext = os.path.splitext(job.audio_path)[1]
                    slug = slugify_vietnamese(job.text[:50])
                    filename = f"{i+1:03d}_{slug}{ext}"
                    zipf.write(job.audio_path, arcname=filename)
                    
    await asyncio.to_thread(create_zip)
    
    headers = {
        "Content-Disposition": f'attachment; filename="batch_{batch_id}.zip"',
    }
    
    return FileResponse(
        path=temp_zip_path,
        media_type="application/zip",
        filename=f"batch_{batch_id}.zip",
        headers=headers,
        background=None  # Can be enhanced to delete the temp file using a background task
    )
