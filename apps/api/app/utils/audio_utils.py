import asyncio
import os
from pathlib import Path

from app.exceptions import TTSJobError
from app.services.audio_storage import validate_audio_file
from app.config import settings

_conversion_locks: dict[str, asyncio.Lock] = {}


def _conversion_lock(output_path: Path) -> asyncio.Lock:
    key = str(output_path.resolve())
    lock = _conversion_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _conversion_locks[key] = lock
    return lock


async def convert_mp3_to_m4a(input_path: str, output_path: str) -> None:
    output = Path(output_path)
    temporary = Path(f"{output_path}.tmp")
    async with _conversion_lock(output):
        if output.exists():
            validate_audio_file(output, mime_type="audio/mp4")
            return

        ffmpeg_binary = settings.ffmpeg_binary_path
        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            input_path,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-vn",
            "-f",
            "ipod",
            str(temporary),
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
                        "FFmpeg conversion failed: "
                        + stderr.decode("utf-8", errors="ignore")
                    ),
                    retryable=False,
                )

            validate_audio_file(temporary, mime_type="audio/mp4")
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


async def convert_mp3_to_wav(input_path: str, output_path: str) -> None:
    output = Path(output_path)
    temporary = Path(f"{output_path}.tmp")
    async with _conversion_lock(output):
        if output.exists():
            validate_audio_file(output, mime_type="audio/wav")
            return

        command = [
            settings.ffmpeg_binary_path,
            "-y",
            "-i",
            input_path,
            "-c:a",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-vn",
            str(temporary),
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
                    message="FFmpeg conversion failed: " + stderr.decode("utf-8", errors="ignore"),
                    retryable=False,
                )
            validate_audio_file(temporary, mime_type="audio/wav")
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


async def get_audio_duration(file_path: Path) -> float | None:
    ffmpeg_binary = settings.ffmpeg_binary_path
    command = [
        ffmpeg_binary,
        "-i",
        str(file_path.resolve()),
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        output = stderr.decode("utf-8", errors="ignore")

        # Parse Duration: HH:MM:SS.ms
        import re

        match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)", output)
        if match:
            h, m, s = match.groups()
            duration = float(h) * 3600 + float(m) * 60 + float(s)
            return duration
        return None
    except Exception:  # noqa: BLE001
        return None
