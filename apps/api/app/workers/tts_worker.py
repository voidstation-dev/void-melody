import asyncio
import logging
import os
import random
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.database import AsyncSessionLocal
from app.exceptions import TTSJobError
from app.media.cache import compute_segment_fingerprint, lookup_cache, store_cache
from app.media.pipeline import concat_audio_parts, probe_audio_duration, transcode_audio
from app.models.tts_job import TTSJobModel
from app.providers.capcut_provider import CapCutProvider
from app.scheduler.cancellation import cancellation_registry
from app.services.audio_cleanup import cleanup_job_artifacts
from app.services.audio_storage import download_audio, validate_audio_file
from app.services.chunk_executor import (
    ChunkLimitExceeded,
    ChunkResult,
    JobSnapshot,
    ensure_chunk_limit,
    execute_chunks_bounded,
)
from app.services.progress_reporter import ProgressReporter
from app.services.raw_response_storage import save_failed_provider_response
from app.services.retry_policy import (
    calculate_retry_delay,
    map_download_error,
    map_provider_error,
)
from app.services.tts_service import claim_job
from app.services.voice_resolver import resolve_voice
from app.utils.text_utils import split_text_into_chunks
from app.utils.timings import JobTimings

logger = logging.getLogger(__name__)


async def process_chunk(
    *,
    index: int,
    text: str,
    provider: Any,
    job: JobSnapshot,
    timings: JobTimings | None = None,
) -> ChunkResult:
    destination = settings.audio_storage_dir / f"{job.id}_part{index}.mp3"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = compute_segment_fingerprint(
        provider_id=job.provider_id,
        text=text,
        voice_type=job.voice_type,
        resource_id=job.resource_id,
        rate=job.rate,
        style=job.style,
        voice_revision=job.voice_revision,
    )

    # 1. Check Generic Audio Segment Cache
    cached_entry = await lookup_cache(fingerprint, session_factory=AsyncSessionLocal)
    if cached_entry is not None and cached_entry.audio_path:
        cached_path = Path(cached_entry.audio_path)
        if cached_path.is_file():
            await asyncio.to_thread(shutil.copy2, str(cached_path), str(destination))
            if timings:
                timings.cache_hit = True
            return ChunkResult(
                index=index,
                path=destination,
                raw_response={"cached": True, "fingerprint": fingerprint},
                mime_type=cached_entry.mime_type or "audio/mpeg",
                size=cached_entry.file_size or destination.stat().st_size,
            )

    # 2. Cache miss: synthesize via provider
    try:
        synth_kwargs: dict[str, Any] = {
            "text": text,
            "voice_type": job.voice_type,
            "resource_id": job.resource_id,
            "rate": job.rate,
            "style": job.style,
        }
        if job.provider_id == "vieneu":
            synth_kwargs["ref_audio"] = job.reference_audio_path
            synth_kwargs["prompt_text"] = job.prompt_text

        result = await provider.synthesize(**synth_kwargs)
    except Exception as exc:
        raise map_provider_error(exc) from exc

    if not result.audio_urls and not result.local_paths:
        raise TTSJobError(
            code="AUDIO_URL_NOT_FOUND",
            message=f"No playable audio URL or local path extracted for chunk {index}",
            retryable=False,
        )

    try:
        if result.local_paths and len(result.local_paths) > 0:
            local_src = Path(result.local_paths[0])
            if local_src != destination:
                await asyncio.to_thread(shutil.move, str(local_src), str(destination))
            mime_type = "audio/mpeg"
            size = destination.stat().st_size
        else:
            mime_type, size = await download_audio(
                url=result.audio_urls[0],
                destination=destination,
                max_bytes=settings.tts_audio_max_bytes,
            )
    except Exception as exc:
        raise map_download_error(exc) from exc

    # 3. Store valid segment into cache
    try:
        await store_cache(
            fingerprint=fingerprint,
            provider_id=job.provider_id,
            voice_key=job.voice_type,
            text=text,
            source_audio_path=destination,
            rate=job.rate,
            style=job.style,
            voice_revision=job.voice_revision,
            mime_type=mime_type,
            session_factory=AsyncSessionLocal,
        )
    except Exception:
        logger.debug("Failed saving segment to cache for fingerprint %s", fingerprint, exc_info=True)

    return ChunkResult(
        index=index,
        path=destination,
        raw_response=result.raw_response,
        mime_type=mime_type,
        size=size,
    )


async def combine_audio_parts(
    *,
    parts: list[Path],
    destination: Path,
    rate: float,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(f"{destination}.tmp")
    if len(parts) == 1:
        if rate == 1.0:
            try:
                parts[0].replace(temporary)
                validate_audio_file(temporary, mime_type="audio/mpeg")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
            return

        command = [
            settings.ffmpeg_binary_path,
            "-y",
            "-i",
            str(parts[0].resolve()),
            "-filter:a",
            f"atempo={rate}",
            "-q:a",
            "2",
            "-f",
            "mp3",
            str(temporary.absolute()),
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise TTSJobError(
                    code="FFMPEG_FAILED",
                    message=(
                        "FFmpeg processing failed: "
                        + stderr.decode("utf-8", errors="ignore")
                    ),
                    retryable=False,
                )
            validate_audio_file(temporary, mime_type="audio/mpeg")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return

    list_file = destination.with_name(f"{destination.stem}_list.txt")
    with list_file.open("w", encoding="utf-8") as output:
        for part in parts:
            escaped_path = str(part.resolve().as_posix()).replace("'", "'\\''")
            output.write(f"file '{escaped_path}'\n")

    ffmpeg_binary = settings.ffmpeg_binary_path
    command = [
        ffmpeg_binary,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file.absolute()),
    ]
    if rate != 1.0:
        command.extend(["-filter:a", f"atempo={rate}", "-q:a", "2"])
    else:
        command.extend(["-c", "copy"])
    command.extend(["-f", "mp3", str(temporary.absolute())])

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise TTSJobError(
                code="FFMPEG_FAILED",
                message=(
                    "FFmpeg processing failed: "
                    + stderr.decode("utf-8", errors="ignore")
                ),
                retryable=False,
            )
        validate_audio_file(temporary, mime_type="audio/mpeg")
        temporary.replace(destination)
    finally:
        list_file.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


async def execute_tts_job_step(
    job_id: str,
    *,
    provider_registry: dict[str, Any] | None = None,
    worker_id: int = 0,
) -> None:
    timings = JobTimings(job_id=job_id)
    async with AsyncSessionLocal() as session:
        if not await claim_job(session, job_id):
            return
        job = await session.get(TTSJobModel, job_id)
        if not job:
            return

        timings.provider = job.provider_id
        active_provider = None
        if provider_registry:
            active_provider = provider_registry.get(job.provider_id)
        if not active_provider:
            active_provider = CapCutProvider(catalog_path=settings.capcut_catalog_path)

        downloaded_files: list[Path] = []
        final_destination = settings.audio_storage_dir / f"{job.id}.mp3"
        raw_responses: list[dict | None] = []

        logger.info(
            "TTS job started",
            extra={
                "job_id": job.id,
                "batch_id": job.batch_id,
                "worker_id": worker_id,
                "attempt": job.attempt_count,
                "voice_type": job.voice_type,
                "text_length": len(job.text),
                "status": "processing",
            },
        )

        try:
            # Resolve voice metadata once per job to snapshot reference audio/prompt
            resolved_ref_audio = None
            resolved_prompt = None
            voice_rev = "v1"
            try:
                resolved_voice = await resolve_voice(session, job.voice_type)
                resolved_ref_audio = resolved_voice.reference_audio_path
                resolved_prompt = resolved_voice.prompt_text
                voice_rev = resolved_voice.voice_revision
            except Exception:
                logger.debug("Voice resolution snapshot skipped for preset: %s", job.voice_type)

            chunks = split_text_into_chunks(job.text) or [""]
            ensure_chunk_limit(
                chunks,
                max_chunks=settings.tts_max_chunks_per_job,
            )

            snapshot = JobSnapshot(
                id=job.id,
                voice_type=job.voice_type,
                resource_id=job.resource_id,
                style=job.style,
                rate=(1.0 if settings.tts_apply_rate_with_ffmpeg else job.rate),
                provider_id=job.provider_id,
                reference_audio_path=resolved_ref_audio,
                prompt_text=resolved_prompt,
                voice_revision=voice_rev,
            )
            raw_responses = [None] * len(chunks)
            progress_reporter = ProgressReporter(
                commit_interval_seconds=settings.tts_progress_commit_interval_seconds,
                commit_step_percent=settings.tts_progress_commit_step_percent,
            )

            async def run_chunk(*, index: int, text: str) -> ChunkResult:
                return await process_chunk(
                    index=index,
                    text=text,
                    provider=active_provider,
                    job=snapshot,
                    timings=timings,
                )

            # In-memory check first (0ms latency, zero DB queries!)
            async def check_cancelled() -> bool:
                if cancellation_registry.is_cancelled(job.id):
                    return True
                return job.cancel_requested

            # Determine chunk concurrency from lane policy
            chunk_conc = (
                settings.vieneu_chunk_concurrency
                if job.provider_id == "vieneu"
                else settings.capcut_chunk_concurrency
            )

            completed = 0
            async for result in execute_chunks_bounded(
                chunks,
                concurrency=chunk_conc,
                process_chunk=run_chunk,
                is_cancelled=check_cancelled,
            ):
                downloaded_files.append(result.path)
                raw_responses[result.index] = result.raw_response
                completed += 1
                if progress_reporter.should_commit(
                    completed=completed,
                    total=len(chunks),
                ):
                    job.progress = int((completed / len(chunks)) * 90)
                    await session.commit()

            downloaded_files.sort(key=lambda path: int(path.stem.rsplit("part", 1)[1]))
            await combine_audio_parts(
                parts=downloaded_files,
                destination=final_destination,
                rate=(job.rate if settings.tts_apply_rate_with_ffmpeg else 1.0),
            )
            for part in downloaded_files:
                part.unlink(missing_ok=True)

            final_size = validate_audio_file(
                final_destination,
                mime_type="audio/mpeg",
            )

            from app.utils.audio_utils import get_audio_duration
            audio_duration = await get_audio_duration(final_destination)

            job.status = "completed"
            job.audio_path = str(final_destination)
            job.audio_mime_type = "audio/mpeg"
            job.audio_file_size = final_size
            job.audio_duration = audio_duration
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)

            # Handle Auto-export asynchronously if configured
            if job.export_path:
                try:
                    export_dir = Path(job.export_path)
                    export_dir.mkdir(parents=True, exist_ok=True)

                    if job.source_file_name:
                        base_name = Path(job.source_file_name).stem
                    else:
                        first_line = job.text.split("\n")[0][:30].strip()
                        safe_name = re.sub(r'[^a-zA-Z0-9\-_ ]', '', first_line).strip()
                        base_name = safe_name or f"melody-{job.id}"

                    format_ext = job.export_format or "mp3"
                    export_file = export_dir / f"{base_name}.{format_ext}"

                    if format_ext == "mp3":
                        await asyncio.to_thread(shutil.copy2, str(final_destination), str(export_file))
                    else:
                        await transcode_audio(
                            input_path=final_destination,
                            output_path=export_file,
                            format=format_ext,
                        )
                except Exception as e:
                    logger.error("Auto-export failed for %s: %s", job.id, e)

            timings.finish()
            logger.info(
                "TTS job completed",
                extra={
                    "job_id": job.id,
                    "batch_id": job.batch_id,
                    "worker_id": worker_id,
                    "attempt": job.attempt_count,
                    "chunk_count": len(chunks),
                    "voice_type": job.voice_type,
                    "text_length": len(job.text),
                    "status": "completed",
                    "duration_ms": timings.total_ms,
                    "cache_hit": timings.cache_hit,
                },
            )

        except Exception as exc:  # noqa: BLE001
            if (
                isinstance(exc, asyncio.CancelledError)
                or getattr(exc, "args", [None])[0] == "Job was cancelled by user"
                or cancellation_registry.is_cancelled(job.id)
            ):
                for part in downloaded_files:
                    part.unlink(missing_ok=True)
                job.status = "cancelled"
                job.progress = 0
                job.error_code = "CANCELLED"
                job.error_message = "Job was cancelled by the user"
                await session.commit()
                logger.info("Job cancelled: %s", job.id)
                return

            if isinstance(exc, ChunkLimitExceeded):
                error = TTSJobError(
                    code="TOO_MANY_CHUNKS",
                    message=str(exc),
                    retryable=False,
                )
            elif isinstance(exc, TTSJobError):
                error = exc
            else:
                error = TTSJobError(
                    code="INTERNAL_ERROR",
                    message=str(exc),
                    retryable=False,
                )

            if error.retryable and job.attempt_count <= settings.tts_max_auto_retries:
                job.status = "queued"
                job.progress = 0
                job.started_at = None
                job.error_code = None
                job.error_message = None
                await session.commit()
                from app.workers.queue_manager import queue_manager

                delay = calculate_retry_delay(
                    attempt=job.attempt_count - 1,
                    base_delay_seconds=settings.tts_retry_base_delay_seconds,
                    retry_after_seconds=error.retry_after_seconds,
                    jitter=random.uniform(0, 1),
                )
                await queue_manager.enqueue_after(
                    job.id,
                    delay_seconds=delay,
                    batch_position=job.batch_position or 0,
                    provider_id=job.provider_id,
                )
                logger.warning(
                    "TTS job scheduled for retry",
                    extra={
                        "job_id": job.id,
                        "batch_id": job.batch_id,
                        "worker_id": worker_id,
                        "attempt": job.attempt_count,
                        "voice_type": job.voice_type,
                        "text_length": len(job.text),
                        "status": "queued",
                        "duration_ms": timings.finish().total_ms,
                        "error_code": error.code,
                    },
                )
                return

            job.status = "failed"
            job.error_code = error.code
            job.error_message = error.message
            if settings.save_raw_provider_responses and any(raw_responses):
                raw_path = save_failed_provider_response(
                    job_id=job.id,
                    payload=raw_responses,
                    directory=settings.raw_response_dir,
                )
                job.raw_response_path = str(raw_path)
            logger.error(
                "TTS job failed",
                exc_info=True,
                extra={
                    "job_id": job.id,
                    "batch_id": job.batch_id,
                    "worker_id": worker_id,
                    "attempt": job.attempt_count,
                    "voice_type": job.voice_type,
                    "text_length": len(job.text),
                    "status": "failed",
                    "duration_ms": timings.finish().total_ms,
                    "error_code": error.code,
                },
            )

        finally:
            cleanup_job_artifacts(
                job.id,
                audio_dir=settings.audio_storage_dir,
            )
            if job.status != "completed":
                final_destination.unlink(missing_ok=True)

        await session.commit()
