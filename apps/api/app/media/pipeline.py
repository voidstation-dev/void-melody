"""Centralized Media Pipeline for bounded FFmpeg execution, transcoding, and audio composition."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Sequence

from app.config import settings
from app.exceptions import TTSJobError
from app.services.audio_storage import validate_audio_file
from app.utils.audio_utils import get_audio_duration

logger = logging.getLogger(__name__)

# Bounded concurrency semaphore to prevent saturating laptop CPU
_ffmpeg_semaphore: asyncio.Semaphore | None = None
_conversion_locks: dict[str, asyncio.Lock] = {}


def _get_ffmpeg_semaphore() -> asyncio.Semaphore:
    global _ffmpeg_semaphore
    if _ffmpeg_semaphore is None:
        _ffmpeg_semaphore = asyncio.Semaphore(settings.media_ffmpeg_concurrency)
    return _ffmpeg_semaphore


def _get_conversion_lock(output_path: Path) -> asyncio.Lock:
    key = str(output_path.resolve())
    lock = _conversion_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _conversion_locks[key] = lock
    return lock


async def concat_audio_parts(
    *,
    parts: Sequence[Path],
    destination: Path,
    rate: float = 1.0,
    output_format: str = "mp3",
) -> tuple[int, float | None]:
    """Concatenate audio chunk parts into a single validated audio file."""
    if not parts:
        raise ValueError("At least one audio part is required for concatenation")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.stem}.tmp{destination.suffix or '.mp3'}")

    if len(parts) == 1 and rate == 1.0 and output_format == "mp3":
        try:
            parts[0].replace(temporary)
            size = validate_audio_file(temporary, mime_type="audio/mpeg")
            temporary.replace(destination)
            duration = await probe_audio_duration(destination)
            return size, duration
        finally:
            temporary.unlink(missing_ok=True)

    list_file = destination.with_name(f"{destination.stem}_concat_list.txt")
    with list_file.open("w", encoding="utf-8") as output:
        for part in parts:
            output.write(f"file '{part.absolute()}'\n")

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

    if output_format == "wav":
        command.extend(["-f", "wav", str(temporary.absolute())])
        mime_type = "audio/wav"
    else:
        command.extend(["-f", "mp3", str(temporary.absolute())])
        mime_type = "audio/mpeg"

    try:
        async with _get_ffmpeg_semaphore():
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

        if process.returncode != 0:
            raise TTSJobError(
                code="FFMPEG_FAILED",
                message="FFmpeg concat failed: " + stderr.decode("utf-8", errors="ignore"),
                retryable=False,
            )

        size = validate_audio_file(temporary, mime_type=mime_type)
        temporary.replace(destination)
        duration = await probe_audio_duration(destination)
        return size, duration
    finally:
        list_file.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)


async def transcode_audio(
    *,
    input_path: str | Path,
    output_path: str | Path,
    format: str = "mp3",
) -> None:
    """Transcode an audio file to mp3, m4a, or wav format with concurrency control."""
    src = Path(input_path)
    dst = Path(output_path)
    temporary = dst.with_name(f"{dst.stem}.tmp{dst.suffix}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    async with _get_conversion_lock(dst):
        if dst.exists():
            expected_mime = (
                "audio/mp4" if format == "m4a" else ("audio/wav" if format == "wav" else "audio/mpeg")
            )
            validate_audio_file(dst, mime_type=expected_mime)
            return

        ffmpeg_binary = settings.ffmpeg_binary_path
        if format == "m4a":
            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                str(src),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-vn",
                "-f",
                "ipod",
                str(temporary),
            ]
            expected_mime = "audio/mp4"
        elif format == "wav":
            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                str(src),
                "-c:a",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-vn",
                str(temporary),
            ]
            expected_mime = "audio/wav"
        else:
            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                str(src),
                "-q:a",
                "2",
                str(temporary),
            ]
            expected_mime = "audio/mpeg"

        try:
            async with _get_ffmpeg_semaphore():
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await process.communicate()

            if process.returncode != 0:
                raise TTSJobError(
                    code="FFMPEG_FAILED",
                    message="FFmpeg conversion failed: " + stderr.decode("utf-8", errors="ignore"),
                    retryable=False,
                )

            validate_audio_file(temporary, mime_type=expected_mime)
            temporary.replace(dst)
        finally:
            temporary.unlink(missing_ok=True)


async def probe_audio_duration(file_path: Path) -> float | None:
    return await get_audio_duration(file_path)
