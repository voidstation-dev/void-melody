"""Canonical 48 kHz mono composition for script line artifacts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.exceptions import TTSJobError
from app.services.audio_storage import validate_audio_file
from app.utils.audio_utils import get_audio_duration


@dataclass(frozen=True)
class CompositionSegment:
    path: Path
    pause_before_ms: int = 0
    pause_after_ms: int = 0


def build_composition_command(
    *,
    segments: list[CompositionSegment],
    destination: Path,
    output_format: str,
    ffmpeg_binary: str,
) -> list[str]:
    if not segments:
        raise ValueError("At least one segment is required")
    if output_format not in {"mp3", "wav"}:
        raise ValueError("Only mp3 and wav are supported")

    command = [ffmpeg_binary, "-y"]
    labels: list[str] = []
    input_index = 0
    filter_lines: list[str] = []

    for segment in segments:
        if segment.pause_before_ms > 0:
            seconds = segment.pause_before_ms / 1000
            command.extend(["-f", "lavfi", "-t", f"{seconds:g}", "-i", f"anullsrc=r=48000:cl=mono:d={seconds:g}"])
            filter_lines.append(f"[{input_index}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=mono[s{input_index}]")
            labels.append(f"[s{input_index}]")
            input_index += 1

        command.extend(["-i", str(segment.path)])
        filter_lines.append(f"[{input_index}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=mono[s{input_index}]")
        labels.append(f"[s{input_index}]")
        input_index += 1

        if segment.pause_after_ms > 0:
            seconds = segment.pause_after_ms / 1000
            command.extend(["-f", "lavfi", "-t", f"{seconds:g}", "-i", f"anullsrc=r=48000:cl=mono:d={seconds:g}"])
            filter_lines.append(f"[{input_index}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=mono[s{input_index}]")
            labels.append(f"[s{input_index}]")
            input_index += 1

    filter_lines.append("".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]")
    command.extend(["-filter_complex", ";".join(filter_lines), "-map", "[out]"])
    command.extend(["-ar", "48000", "-ac", "1"])
    if output_format == "mp3":
        command.extend(["-codec:a", "libmp3lame", "-q:a", "2"])
    else:
        command.extend(["-codec:a", "pcm_s16le"])
    command.append(str(destination.with_name(f"{destination.stem}.tmp{destination.suffix}")))
    return command


async def compose_script_audio(
    *,
    segments: list[CompositionSegment],
    destination: Path,
    output_format: str,
) -> tuple[int, float | None]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.stem}.tmp{destination.suffix}")
    command = build_composition_command(
        segments=segments,
        destination=destination,
        output_format=output_format,
        ffmpeg_binary=settings.ffmpeg_binary_path,
    )
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise TTSJobError(
                code="MIX_FAILED",
                message="FFmpeg composition failed: " + stderr.decode("utf-8", errors="ignore"),
                retryable=True,
            )
        mime_type = "audio/mpeg" if output_format == "mp3" else "audio/wav"
        size = validate_audio_file(temporary, mime_type=mime_type)
        temporary.replace(destination)
        return size, await get_audio_duration(destination)
    finally:
        temporary.unlink(missing_ok=True)
