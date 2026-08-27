from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.database import get_async_session
from app.config import settings
from app.services.plan_enforcement import check_request_feature
from app.models.emotional_script import (
    EmotionalScriptModel,
    ScriptAudioCacheModel,
    ScriptRenderModel,
    ScriptRenderSegmentModel,
)
from app.schemas.emotional_script import EmotionalScriptDocument
from app.schemas.script_render import (
    ParseScriptRequest,
    PreviewResponse,
    RenderCreateRequest,
    RenderResponse,
    RenderSegmentResponse,
    RetryRenderRequest,
    ExportRenderRequest,
    ScriptCreateRequest,
    ScriptParseResponse,
    ScriptPatchRequest,
    ScriptSummaryResponse,
)
from app.services.global_delivery_interpreter import interpret_global_delivery
from app.services.script_parser import parse_script
from app.services.script_render_planner import compute_segment_fingerprint
from app.services.script_store import (
    ScriptNotFound,
    ScriptRevisionConflict,
    create_script,
    delete_script,
    document_from_row,
    get_script,
    list_scripts,
    update_script,
)
from app.services.vieneu_delivery_resolver import resolve_vieneu_delivery
from app.services.voice_resolver import VoiceResolutionError, resolve_voice
from app.workers.script_render_queue import script_render_queue

router = APIRouter()


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _script_response(row: EmotionalScriptModel) -> ScriptSummaryResponse:
    return ScriptSummaryResponse(
        id=row.id,
        title=row.title,
        revision=row.revision,
        schema_version=row.schema_version,
        document=document_from_row(row),
        created_at=_iso(row.created_at),
        updated_at=_iso(row.updated_at),
    )


def _render_response(
    render: ScriptRenderModel,
    segments: list[ScriptRenderSegmentModel],
) -> RenderResponse:
    return RenderResponse(
        id=render.id,
        script_id=render.script_id,
        script_revision=render.script_revision,
        status=render.status,
        stage=render.stage,
        progress=render.progress,
        total_segments=render.total_segments,
        cached_segments=render.cached_segments,
        completed_segments=render.completed_segments,
        failed_segments=render.failed_segments,
        output_format=render.output_format,
        output_duration=render.output_duration,
        output_file_size=render.output_file_size,
        output_url=f"/api/v1/script-renders/{render.id}/audio" if render.output_path else None,
        error_code=render.error_code,
        error_message=render.error_message,
        segments=[
            RenderSegmentResponse(
                id=segment.id,
                line_id=segment.line_id,
                ordinal=segment.ordinal,
                voice_id=segment.voice_id,
                voice_mode=segment.voice_mode,
                status=segment.status,
                progress=segment.progress,
                request_fingerprint=segment.request_fingerprint,
                audio_url=(f"/api/v1/script-renders/{render.id}/audio" if segment.audio_path else None),
                error_code=segment.error_code,
                error_message=segment.error_message,
            )
            for segment in segments
        ],
    )


@router.post("/scripts/parse", response_model=ScriptParseResponse)
async def parse_script_endpoint(request: ParseScriptRequest) -> ScriptParseResponse:
    try:
        document = parse_script(
            request.content,
            format=request.format,
            title=request.title,
            original_name=request.original_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_SCRIPT", "message": str(exc)}) from exc
    return ScriptParseResponse(
        document=document,
        line_count=len(document.lines),
        speaker_count=len(document.speakers),
        warning_count=len(document.warnings),
    )


@router.post("/scripts", response_model=ScriptSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_script_endpoint(
    request: ScriptCreateRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ScriptSummaryResponse:
    if not request.document.lines:
        raise HTTPException(status_code=422, detail={"code": "EMPTY_SCRIPT", "message": "Script must contain at least one line."})
    row = await create_script(session, request.document, title=request.title)
    return _script_response(row)


@router.get("/scripts", response_model=list[ScriptSummaryResponse])
async def list_scripts_endpoint(session: AsyncSession = Depends(get_async_session)) -> list[ScriptSummaryResponse]:
    return [_script_response(row) for row in await list_scripts(session)]


@router.get("/scripts/{script_id}", response_model=ScriptSummaryResponse)
async def get_script_endpoint(script_id: str, session: AsyncSession = Depends(get_async_session)) -> ScriptSummaryResponse:
    try:
        return _script_response(await get_script(session, script_id))
    except ScriptNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "SCRIPT_NOT_FOUND", "message": "Script not found."}) from exc


@router.patch("/scripts/{script_id}", response_model=ScriptSummaryResponse)
async def patch_script_endpoint(
    script_id: str,
    request: ScriptPatchRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ScriptSummaryResponse:
    try:
        row = await update_script(
            session,
            script_id,
            request.document,
            expected_revision=request.expected_revision,
        )
    except ScriptNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "SCRIPT_NOT_FOUND", "message": "Script not found."}) from exc
    except ScriptRevisionConflict as exc:
        raise HTTPException(status_code=409, detail={"code": "SCRIPT_REVISION_CONFLICT", "message": str(exc)}) from exc
    return _script_response(row)


@router.delete("/scripts/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script_endpoint(script_id: str, session: AsyncSession = Depends(get_async_session)) -> None:
    try:
        await delete_script(session, script_id)
    except ScriptNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "SCRIPT_NOT_FOUND", "message": "Script not found."}) from exc


@router.post("/scripts/{script_id}/renders", response_model=RenderResponse, status_code=status.HTTP_201_CREATED)
async def create_script_render(
    script_id: str,
    request: RenderCreateRequest,
    fastapi_request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> RenderResponse:
    check_request_feature(fastapi_request, "audio_studio")
    if request.output_format not in {"mp3", "wav"}:
        raise HTTPException(status_code=422, detail={"code": "INVALID_OUTPUT_FORMAT", "message": "Only MP3 and WAV are supported."})
    try:
        script = await get_script(session, script_id)
    except ScriptNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "SCRIPT_NOT_FOUND", "message": "Script not found."}) from exc

    document = document_from_row(script)
    global_delivery = interpret_global_delivery(document.defaults.global_delivery_prompt)
    speaker_map = {speaker.id: speaker for speaker in document.speakers}
    resolved_segments: list[ScriptRenderSegmentModel] = []
    blocking_errors: list[dict[str, str]] = []
    for ordinal, line in enumerate(document.lines):
        speaker = speaker_map.get(line.speaker_id) if line.speaker_id else None
        voice_id = (speaker.voice_id if speaker else None) or document.defaults.voice_id
        if not voice_id:
            blocking_errors.append({"code": "VOICE_NOT_ASSIGNED", "line_id": line.id})
            continue
        try:
            resolved_voice = await resolve_voice(session, voice_id)
        except VoiceResolutionError as exc:
            blocking_errors.append({"code": exc.code, "line_id": line.id})
            continue
        voice_mode = "CLONE" if resolved_voice.source == "custom" else "PRESET"
        resolved = resolve_vieneu_delivery(
            line,
            voice_id=voice_id,
            voice_mode=voice_mode,
            global_delivery=global_delivery,
            base_rate=document.defaults.base_rate,
        )
        fingerprint = compute_segment_fingerprint(
            line=line,
            voice_id=voice_id,
            voice_mode=voice_mode,
            voice_revision=resolved_voice.voice_revision,
            global_delivery=global_delivery,
            base_rate=document.defaults.base_rate,
        )
        cache = await session.get(ScriptAudioCacheModel, fingerprint)
        status_value = "reused" if cache and cache.audio_path else "pending"
        resolved_segments.append(
            ScriptRenderSegmentModel(
                script_id=script.id,
                line_id=line.id,
                ordinal=ordinal,
                voice_id=voice_id,
                voice_mode=voice_mode,
                request_fingerprint=fingerprint,
                resolved_request_json=json.dumps(
                    {"line": line.model_dump(mode="json"), "resolved": resolved.as_dict()},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                status=status_value,
                audio_path=cache.audio_path if cache else None,
                audio_duration=cache.audio_duration if cache else None,
                file_size=cache.file_size if cache else None,
            )
        )

    if blocking_errors:
        raise HTTPException(status_code=422, detail={"code": "PREFLIGHT_BLOCKED", "errors": blocking_errors})
    if not resolved_segments:
        raise HTTPException(status_code=422, detail={"code": "EMPTY_SCRIPT", "message": "Script must contain at least one renderable line."})

    render = ScriptRenderModel(
        script_id=script.id,
        script_revision=script.revision,
        status="queued",
        stage="planning",
        total_segments=len(resolved_segments),
        cached_segments=sum(segment.status == "reused" for segment in resolved_segments),
        completed_segments=sum(segment.status == "reused" for segment in resolved_segments),
        output_format=request.output_format,
    )
    session.add(render)
    await session.flush()
    for segment in resolved_segments:
        segment.render_id = render.id
        session.add(segment)
    await session.commit()
    await session.refresh(render)
    result = await session.execute(select(ScriptRenderSegmentModel).where(ScriptRenderSegmentModel.render_id == render.id).order_by(ScriptRenderSegmentModel.ordinal))
    segments = list(result.scalars().all())
    try:
        await script_render_queue.enqueue(render.id)
    except RuntimeError:
        # The API can be used in tests or a short-lived CLI before lifespan startup.
        pass
    return _render_response(render, segments)


@router.get("/script-renders/{render_id}", response_model=RenderResponse)
async def get_script_render(render_id: str, session: AsyncSession = Depends(get_async_session)) -> RenderResponse:
    render = await session.get(ScriptRenderModel, render_id)
    if render is None:
        raise HTTPException(status_code=404, detail={"code": "RENDER_NOT_FOUND", "message": "Script render not found."})
    result = await session.execute(select(ScriptRenderSegmentModel).where(ScriptRenderSegmentModel.render_id == render.id).order_by(ScriptRenderSegmentModel.ordinal))
    return _render_response(render, list(result.scalars().all()))


@router.post("/script-renders/{render_id}/cancel", response_model=RenderResponse)
async def cancel_script_render(render_id: str, session: AsyncSession = Depends(get_async_session)) -> RenderResponse:
    render = await session.get(ScriptRenderModel, render_id)
    if render is None:
        raise HTTPException(status_code=404, detail={"code": "RENDER_NOT_FOUND", "message": "Script render not found."})
    render.cancel_requested = True
    if render.status in {"queued", "planning"}:
        render.status = "cancelled"
        render.stage = "cancelled"
    await session.commit()
    result = await session.execute(select(ScriptRenderSegmentModel).where(ScriptRenderSegmentModel.render_id == render.id).order_by(ScriptRenderSegmentModel.ordinal))
    return _render_response(render, list(result.scalars().all()))


@router.post("/script-renders/{render_id}/retry", response_model=RenderResponse)
async def retry_script_render(
    render_id: str,
    request: RetryRenderRequest,
    session: AsyncSession = Depends(get_async_session),
) -> RenderResponse:
    render = await session.get(ScriptRenderModel, render_id)
    if render is None:
        raise HTTPException(status_code=404, detail={"code": "RENDER_NOT_FOUND", "message": "Script render not found."})
    result = await session.execute(select(ScriptRenderSegmentModel).where(ScriptRenderSegmentModel.render_id == render.id).order_by(ScriptRenderSegmentModel.ordinal))
    segments = list(result.scalars().all())
    scope = request.scope if request.scope in {"failed", "stale", "all"} else "failed"
    for segment in segments:
        if scope == "all" or (scope == "failed" and segment.status == "failed") or (scope == "stale" and segment.status in {"failed", "pending"}):
            segment.status = "pending"
            segment.error_code = None
            segment.error_message = None
            segment.retryable = False
    render.cancel_requested = False
    render.status = "queued"
    render.stage = "planning"
    render.error_code = None
    render.error_message = None
    await session.commit()
    try:
        await script_render_queue.enqueue(render.id)
    except RuntimeError:
        pass
    return _render_response(render, segments)


@router.get("/script-renders/{render_id}/audio")
async def get_script_render_audio(render_id: str, session: AsyncSession = Depends(get_async_session)) -> FileResponse:
    render = await session.get(ScriptRenderModel, render_id)
    if render is None or not render.output_path:
        raise HTTPException(status_code=404, detail={"code": "AUDIO_NOT_READY", "message": "Script audio is not ready."})
    path = Path(render.output_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "AUDIO_NOT_FOUND", "message": "Script audio artifact is missing."})
    media_type = render.output_mime_type or ("audio/mpeg" if render.output_format == "mp3" else "audio/wav")
    return FileResponse(path, media_type=media_type, filename=f"script-{render.id}.{render.output_format}")


@router.post("/script-renders/{render_id}/export")
async def export_script_render(
    render_id: str,
    request: ExportRenderRequest,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    render = await session.get(ScriptRenderModel, render_id)
    if render is None or not render.output_path:
        raise HTTPException(status_code=409, detail={"code": "AUDIO_NOT_READY", "message": "Complete the render before exporting."})
    if request.output_format != render.output_format:
        raise HTTPException(status_code=422, detail={"code": "FORMAT_NOT_AVAILABLE", "message": "Render the requested output format first."})
    source = Path(render.output_path)
    directory = Path(request.directory) if request.directory else settings.audio_storage_dir / "exports"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"script-{render.id}.{render.output_format}"
    shutil.copy2(source, destination)
    return {"status": "exported", "path": str(destination)}


@router.post("/scripts/{script_id}/lines/{line_id}/preview", response_model=PreviewResponse)
async def preview_script_line(script_id: str, line_id: str, session: AsyncSession = Depends(get_async_session)) -> PreviewResponse:
    script = await get_script(session, script_id)
    document = document_from_row(script)
    line = next((item for item in document.lines if item.id == line_id), None)
    if line is None:
        raise HTTPException(status_code=404, detail={"code": "LINE_NOT_FOUND", "message": "Script line not found."})
    speaker = next((item for item in document.speakers if item.id == line.speaker_id), None)
    voice_id = (speaker.voice_id if speaker else None) or document.defaults.voice_id
    if not voice_id:
        raise HTTPException(status_code=422, detail={"code": "VOICE_NOT_ASSIGNED", "message": "Assign a voice before previewing this line."})
    try:
        resolved_voice = await resolve_voice(session, voice_id)
    except VoiceResolutionError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc
    resolved = resolve_vieneu_delivery(
        line,
        voice_id=voice_id,
        voice_mode="CLONE" if resolved_voice.source == "custom" else "PRESET",
    )
    return PreviewResponse(
        line_id=line.id,
        emitted_text=resolved.emitted_text,
        native_cues=resolved.native_cues,
        approximated_intents=resolved.approximated_intents,
        unsupported_intents=resolved.unsupported_intents,
        warnings=resolved.warnings,
    )
