"""Speech transcription API for Voice Lab and local STT."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.config import settings
from app.services.plan_enforcement import check_request_feature
from app.services.voice_analysis import normalized_extension, save_upload_to_temp

router = APIRouter()
logger = logging.getLogger(__name__)


async def _extract_segment_to_wav(
    source_path: Path,
    output_path: Path,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> None:
    """Extract a slice of audio and normalize to 16kHz mono WAV for Whisper / STT."""
    ffmpeg = settings.ffmpeg_binary_path
    cmd = [ffmpeg, "-y"]
    if start_seconds is not None and start_seconds > 0:
        cmd.extend(["-ss", f"{start_seconds:.3f}"])
    cmd.extend(["-i", str(source_path)])
    if end_seconds is not None and start_seconds is not None and end_seconds > start_seconds:
        duration = end_seconds - start_seconds
        cmd.extend(["-t", f"{duration:.3f}"])
    elif end_seconds is not None and end_seconds > 0:
        cmd.extend(["-t", f"{end_seconds:.3f}"])

    cmd.extend(["-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(output_path)])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("FFmpeg extraction failed: %s", stderr.decode("utf-8", errors="ignore"))
        raise RuntimeError("Failed to extract audio segment for transcription.")


@router.post("/speech/transcribe")
async def transcribe_speech(
    file: UploadFile = File(...),  # noqa: B008
    start_seconds: float | None = Form(default=None),
    end_seconds: float | None = Form(default=None),
    language: str = Form(default="vi"),
    model: str = Form(default="small"),
    request: Request = None,  # noqa: B008
):
    """Transcribe an audio file or selected segment into text."""
    check_request_feature(request, "transcription")
    ext = normalized_extension(file.filename)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format. Choose WAV, MP3, or M4A.",
        )

    temp_source = None
    temp_wav = None
    try:
        temp_dir = settings.custom_voices_dir / ".transcribe"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_source = await save_upload_to_temp(
            file,
            directory=temp_dir,
            max_bytes=settings.tts_audio_max_bytes,
        )

        temp_wav = temp_dir / f"{uuid.uuid4().hex}_segment.wav"
        await _extract_segment_to_wav(
            temp_source,
            temp_wav,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )

        # 1. Try local Faster-Whisper
        try:
            from faster_whisper import WhisperModel

            model_size = model if model in ("tiny", "base", "small", "medium", "large-v3-turbo", "large-v3", "large") else "small"
            if model_size == "large-v3-turbo":
                model_size = "large-v3"
            whisper_engine = WhisperModel(model_size, device="cpu", compute_type="int8")
            segments, _ = whisper_engine.transcribe(str(temp_wav), language=language if language != "auto" else None)
            text = " ".join(s.text.strip() for s in segments).strip()
            if text:
                logger.info("Transcribed with faster-whisper (%s): %s", model, text)
                return {"text": text, "engine": "faster-whisper", "model": model}
        except ImportError:
            logger.debug("faster-whisper not installed in environment")
        except Exception as e:
            logger.warning("faster-whisper transcription error: %s", e)

        # 2. Try standard OpenAI Whisper
        try:
            import whisper

            model_size = model if model in ("tiny", "base", "small", "medium", "large") else "small"
            model_obj = whisper.load_model(model_size)
            result = model_obj.transcribe(str(temp_wav), language=language if language != "auto" else None)
            text = result.get("text", "").strip()
            if text:
                logger.info("Transcribed with openai-whisper (%s): %s", model, text)
                return {"text": text, "engine": "openai-whisper", "model": model}
        except ImportError:
            logger.debug("openai-whisper not installed in environment")
        except Exception as e:
            logger.warning("openai-whisper transcription error: %s", e)

        # 3. Try CapCut STT
        try:
            from capcut_tts_api import CapCutClient

            client = CapCutClient()
            capcut_lang = "vi-VN" if language.startswith("vi") else "en-US"
            query_res = await asyncio.to_thread(
                client.transcribe_file,
                file_path=str(temp_wav),
                language=capcut_lang,
                translation_language=capcut_lang,
                wait=True,
            )
            subtitles = client.extract_subtitles(query_res)
            text = (getattr(subtitles, "full_text", "") or "").strip()
            if text:
                logger.info("Transcribed with CapCut STT: %s", text)
                return {"text": text, "engine": "capcut-stt", "model": "cloud"}
        except Exception as e:
            logger.warning("CapCut STT failed: %s", e)

        return {"text": "", "engine": "none", "model": model}

    except Exception as exc:
        logger.exception("Transcribe failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech transcription failed: {exc}",
        ) from exc
    finally:
        if temp_source is not None:
            temp_source.unlink(missing_ok=True)
        if temp_wav is not None:
            temp_wav.unlink(missing_ok=True)
