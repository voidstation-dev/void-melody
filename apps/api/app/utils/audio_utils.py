"""Audio utility helpers delegating to the centralized media pipeline."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from app.config import settings


async def convert_mp3_to_m4a(input_path: str, output_path: str) -> None:
    from app.media.pipeline import transcode_audio

    await transcode_audio(
        input_path=input_path,
        output_path=output_path,
        format="m4a",
    )


async def convert_mp3_to_wav(input_path: str, output_path: str) -> None:
    from app.media.pipeline import transcode_audio

    await transcode_audio(
        input_path=input_path,
        output_path=output_path,
        format="wav",
    )


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
        match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}\.\d+)", output)
        if match:
            h, m, s = match.groups()
            duration = float(h) * 3600 + float(m) * 60 + float(s)
            return duration
        return None
    except Exception:  # noqa: BLE001
        return None
