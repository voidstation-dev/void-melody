import asyncio
import logging
import os
import tempfile
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import select
from vieneu_core.engine import ModelManager
from vieneu_core.fixtures import FIXTURE_VOICES

from app.database import AsyncSessionLocal
from app.models.custom_voice import CustomVoiceModel
from app.providers.base import ProviderResult, ProviderVoice
from app.config import settings

logger = logging.getLogger(__name__)


class VieneuProvider:
    def __init__(self):
        self.manager = ModelManager()
        self._inference_semaphore = asyncio.Semaphore(1)

    async def list_voices(self, language: str | None = None) -> list[ProviderVoice]:
        return [
            ProviderVoice(
                language_short="vi",
                language_code="vi-VN",
                voice_type=v.voice_id,
                display_name=v.display_name,
                resource_id=None,
                provider_id="vieneu",
            )
            for v in FIXTURE_VOICES
        ]

    async def synthesize(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None,
        rate: float,
        style: str | None = None,
    ) -> ProviderResult:
        logger.info("VieneuProvider synthesizing %s", voice_type)
        engine = await self.manager.get_engine()
        
        voice_id, ref_audio, prompt_text = await self._resolve_custom_voice(voice_type)

        # inference is cpu bound, run in thread behind semaphore
        async with self._inference_semaphore:
            wav = await asyncio.to_thread(
                engine.infer,
                text=text,
                voice=voice_id,
                ref_audio=ref_audio,
                prompt_text=prompt_text,
                style=style or "tu_nhien",
                apply_watermark=False,
            )

        fd, wav_path_str = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        wav_path = Path(wav_path_str)

        try:
            await asyncio.to_thread(engine.save, wav, wav_path)

            mp3_path = wav_path.with_suffix(".mp3")
            ffmpeg_binary = settings.ffmpeg_binary_path

            command = [
                ffmpeg_binary,
                "-y",
                "-i",
                str(wav_path),
                "-q:a",
                "2",
                str(mp3_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg conversion failed: {stderr.decode('utf-8', errors='ignore')}"
                )

            return ProviderResult(
                raw_response={"engine": "vieneu-v3-turbo", "voice": voice_type},
                audio_urls=[],
                local_paths=[str(mp3_path)],
            )
        finally:
            wav_path.unlink(missing_ok=True)

    async def preflight_clone_reference(self, reference_audio_path: Path) -> None:
        """Run the real speaker-enrollment path before a profile is persisted."""

        engine = await self.manager.get_engine()
        async with self._inference_semaphore:
            await asyncio.to_thread(
                engine.encode_reference,
                str(reference_audio_path),
                denoise=True,
            )

    async def synthesize_stream(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None,
        rate: float,
        style: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        engine = await self.manager.get_engine()
        ffmpeg_binary = settings.ffmpeg_binary_path

        command = [
            ffmpeg_binary,
            "-y",
            "-f",
            "f32le",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-f",
            "mp3",
            "pipe:1",
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        voice_id, ref_audio, prompt_text = await self._resolve_custom_voice(voice_type)

        async def feed_pcm():
            try:
                # The infer_stream method is a generator, so we must advance it in a thread.
                gen = engine.infer_stream(
                    text=text,
                    voice=voice_id,
                    ref_audio=ref_audio,
                    prompt_text=prompt_text,
                    style=style or "tu_nhien",
                    apply_watermark=False,
                )

                def get_next():
                    try:
                        return next(gen)
                    except StopIteration:
                        return None

                while True:
                    async with self._inference_semaphore:
                        chunk = await asyncio.to_thread(get_next)

                    if chunk is None:
                        break

                    if process.stdin:
                        process.stdin.write(chunk.tobytes())
                        await process.stdin.drain()
            except Exception:
                logger.exception("Error in PCM feeder")
            finally:
                if process.stdin:
                    process.stdin.close()
                    try:
                        await process.stdin.wait_closed()
                    except Exception:  # noqa: S110, BLE001
                        pass
        feeder_task = asyncio.create_task(feed_pcm())

        try:
            if not process.stdout:
                raise RuntimeError("Process stdout is None")
            while True:
                data = await process.stdout.read(8192)
                if not data:
                    break
                yield data
        finally:
            feeder_task.cancel()
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()

    async def _resolve_custom_voice(self, voice_type: str) -> tuple[str | None, str | None, str | None]:
        try:
            uuid.UUID(voice_type)
        except ValueError:
            return voice_type, None, None

        async with AsyncSessionLocal() as session:
            stmt = select(CustomVoiceModel).where(CustomVoiceModel.id == voice_type)
            result = await session.execute(stmt)
            voice = result.scalars().first()
            if voice and voice.reference_audio_path:
                return None, voice.reference_audio_path, voice.transcript
        
        return voice_type, None, None
