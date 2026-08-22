"""Execution service for isolated Emotional Script renders."""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.exceptions import TTSJobError
from app.models.emotional_script import (
    ScriptAudioCacheModel,
    ScriptRenderModel,
    ScriptRenderSegmentModel,
)
from app.services.audio_storage import validate_audio_file
from app.services.script_audio_composer import CompositionSegment, compose_script_audio
from app.services.vieneu_delivery_resolver import ResolvedVieNeuDelivery
from app.services.vieneu_script_synthesis import VieNeuScriptSynthesisAdapter
from app.workers.queue_manager import queue_manager


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _map_error(exc: Exception) -> tuple[str, str, bool]:
    if isinstance(exc, TTSJobError):
        return exc.code, exc.message, exc.retryable
    return "INTERNAL", str(exc), False


async def _wait_for_standard_priority() -> None:
    # The standard queue is intentionally higher priority. We only yield
    # between script units; an already-running VieNeu call remains bounded by
    # the planner's unit size.
    while queue_manager.queue.qsize() > 0:
        await asyncio.sleep(0.1)


async def _save_script_artifact(
    *,
    session,
    segment: ScriptRenderSegmentModel,
    provider_result,
) -> None:
    if provider_result.local_paths:
        source = Path(provider_result.local_paths[0])
        validate_audio_file(source, mime_type="audio/mpeg")
    else:
        raise TTSJobError(
            code="AUDIO_INVALID",
            message="VieNeu script synthesis did not return a local artifact.",
            retryable=False,
        )

    cache_dir = settings.audio_storage_dir / "script-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / f"{segment.request_fingerprint}.mp3"
    if source.resolve() != destination.resolve():
        if destination.exists():
            source.unlink(missing_ok=True)
        else:
            shutil.move(str(source), str(destination))
    size = validate_audio_file(destination, mime_type="audio/mpeg")
    cache = await session.get(ScriptAudioCacheModel, segment.request_fingerprint)
    if cache is None:
        cache = ScriptAudioCacheModel(
            fingerprint=segment.request_fingerprint,
            audio_path=str(destination),
            voice_id=segment.voice_id,
            voice_mode=segment.voice_mode,
            file_size=size,
        )
        session.add(cache)
    else:
        cache.audio_path = str(destination)
        cache.file_size = size
        cache.last_used_at = _now()
    segment.audio_path = str(destination)
    segment.file_size = size
    segment.status = "ready"
    segment.progress = 100
    segment.completed_at = _now()


async def execute_script_render(render_id: str) -> None:
    async with AsyncSessionLocal() as session:
        render = await session.get(ScriptRenderModel, render_id)
        if render is None:
            return
        result = await session.execute(
            select(ScriptRenderSegmentModel)
            .where(ScriptRenderSegmentModel.render_id == render_id)
            .order_by(ScriptRenderSegmentModel.ordinal)
        )
        segments = list(result.scalars().all())
        render.status = "rendering"
        render.stage = "rendering"
        render.started_at = _now()
        await session.commit()

        provider = queue_manager.provider_registry.get("vieneu")
        if provider is None:
            render.status = "failed"
            render.error_code = "VIENEU_RUNTIME_UNAVAILABLE"
            render.error_message = "VieNeu provider is not registered."
            await session.commit()
            return
        adapter = VieNeuScriptSynthesisAdapter(provider=provider)

        for segment in segments:
            await session.refresh(render, ["cancel_requested"])
            if render.cancel_requested:
                render.status = "cancelled"
                render.stage = "cancelled"
                await session.commit()
                return
            if segment.status == "reused" and segment.audio_path and Path(segment.audio_path).is_file():
                continue
            if segment.status == "reused":
                segment.status = "pending"
                segment.audio_path = None

            while True:
                await _wait_for_standard_priority()
                segment.status = "rendering"
                segment.started_at = _now()
                segment.attempt_count += 1
                await session.commit()
                try:
                    payload = json.loads(segment.resolved_request_json)
                    resolved = ResolvedVieNeuDelivery(**payload["resolved"])
                    provider_result = await adapter.synthesize(resolved)
                    await _save_script_artifact(
                        session=session,
                        segment=segment,
                        provider_result=provider_result,
                    )
                    break
                except Exception as exc:  # noqa: BLE001 - persisted into segment taxonomy
                    code, message, retryable = _map_error(exc)
                    if retryable and segment.attempt_count <= settings.tts_max_auto_retries:
                        segment.status = "pending"
                        segment.error_code = code
                        segment.error_message = message
                        segment.retryable = True
                        await session.commit()
                        await asyncio.sleep(settings.tts_retry_base_delay_seconds)
                        continue
                    segment.status = "failed"
                    segment.error_code = code
                    segment.error_message = message
                    segment.retryable = retryable
                    break
            await session.commit()

            ready_count = sum(item.status in {"ready", "reused"} for item in segments)
            failed_count = sum(item.status == "failed" for item in segments)
            render.completed_segments = ready_count
            render.failed_segments = failed_count
            render.progress = int((ready_count / max(1, len(segments))) * 90)
            await session.commit()

        render.completed_segments = sum(item.status in {"ready", "reused"} for item in segments)
        render.failed_segments = sum(item.status == "failed" for item in segments)
        if render.failed_segments:
            render.status = "partial_failed" if render.completed_segments else "failed"
            render.stage = "rendering"
            render.progress = int((render.completed_segments / max(1, len(segments))) * 100)
            await session.commit()
            return

        render.status = "mixing"
        render.stage = "mixing"
        await session.commit()
        composition_segments: list[CompositionSegment] = []
        for segment in segments:
            payload = json.loads(segment.resolved_request_json)
            resolved_payload = payload["resolved"]
            composition_segments.append(
                CompositionSegment(
                    Path(segment.audio_path),
                    pause_before_ms=int(resolved_payload.get("pause_before_ms", 0)),
                    pause_after_ms=int(resolved_payload.get("pause_after_ms", 0)),
                )
            )
        output_dir = settings.audio_storage_dir / "scripts"
        output_path = output_dir / f"{render.id}.{render.output_format}"
        try:
            size, duration = await compose_script_audio(
                segments=composition_segments,
                destination=output_path,
                output_format=render.output_format,
            )
        except Exception as exc:  # noqa: BLE001 - preserve prior output on failure
            code, message, retryable = _map_error(exc)
            render.status = "failed"
            render.stage = "mixing"
            render.error_code = code
            render.error_message = message
            await session.commit()
            return

        render.status = "completed"
        render.stage = "completed"
        render.progress = 100
        render.output_path = str(output_path)
        render.output_mime_type = "audio/mpeg" if render.output_format == "mp3" else "audio/wav"
        render.output_file_size = size
        render.output_duration = duration
        render.completed_at = _now()
        await session.commit()


async def recover_interrupted_script_renders() -> None:
    """Mark in-flight script work as resumable after a process restart."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScriptRenderModel).where(
                ScriptRenderModel.status.in_(["planning", "rendering", "mixing"])
            )
        )
        renders = list(result.scalars().all())
        for render in renders:
            render.status = "interrupted"
            render.stage = "interrupted"
            segments_result = await session.execute(
                select(ScriptRenderSegmentModel).where(
                    ScriptRenderSegmentModel.render_id == render.id,
                    ScriptRenderSegmentModel.status == "rendering",
                )
            )
            for segment in segments_result.scalars().all():
                segment.status = "pending"
        if renders:
            await session.commit()
