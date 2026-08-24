import asyncio
import logging
import os
import tempfile
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import select
from vieneu_core.engine import ModelManager
from app.database import AsyncSessionLocal
from app.models.custom_voice import CustomVoiceModel
from app.providers.base import ProviderResult, ProviderVoice, SynthesisOptions
from app.config import settings
from app.services.vieneu_preset_catalog import list_vieneu_preset_voices

logger = logging.getLogger(__name__)


class VieneuProvider:
    def __init__(self):
        self.manager = ModelManager()
        self._inference_semaphore = asyncio.Semaphore(1)

    async def list_voices(self, language: str | None = None) -> list[ProviderVoice]:
        voices = list(list_vieneu_preset_voices())
        if language is None:
            return voices
        return [
            voice for voice in voices
            if voice.language_code.casefold() == language.casefold()
        ]

    async def synthesize(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None,
        rate: float,
        style: str | None = None,
        options: SynthesisOptions | None = None,
        ref_audio: str | None = None,
        prompt_text: str | None = None,
    ) -> ProviderResult:
        logger.info("VieneuProvider synthesizing %s", voice_type)
        engine = await self.manager.get_engine()
        
        use_ref_codes = True
        if ref_audio is None and prompt_text is None:
            resolved_tup = await self._resolve_custom_voice(voice_type)
            voice_spec, ref_audio, prompt_text = resolved_tup[0], resolved_tup[1], resolved_tup[2]
            if len(resolved_tup) > 3:
                use_ref_codes = resolved_tup[3]
        else:
            voice_spec = None

        infer_kwargs = {
            "text": text,
            "voice": voice_spec,
            "ref_audio": ref_audio,
            "prompt_text": prompt_text,
            "style": style or "tu_nhien",
            "apply_watermark": False,
        }
        if isinstance(voice_spec, dict):
            infer_kwargs["use_ref_codes"] = use_ref_codes

        # inference is cpu bound, run in thread behind semaphore
        async with self._inference_semaphore:
            wav = await asyncio.to_thread(
                engine.infer,
                **infer_kwargs,
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

    async def synthesize_script(
        self,
        *,
        text: str,
        voice_type: str,
        rate: float,
    ) -> ProviderResult:
        """Synthesize an Emotional Script unit without the deprecated style arg.

        The standard TTS path intentionally keeps its existing ``style``
        behavior. This separate method is the only entry point used by the
        script adapter, so future VieNeu runtime changes stay isolated.
        """
        del rate  # VieNeu v3 Turbo has no native rate control in this path.
        logger.info("VieneuProvider synthesizing script unit for %s", voice_type)
        engine = await self.manager.get_engine()
        resolved_tup = await self._resolve_custom_voice(voice_type)
        voice_spec, ref_audio, prompt_text = resolved_tup[0], resolved_tup[1], resolved_tup[2]
        use_ref_codes = resolved_tup[3] if len(resolved_tup) > 3 else True

        infer_kwargs = {
            "text": text,
            "voice": voice_spec,
            "ref_audio": ref_audio,
            "prompt_text": prompt_text,
            "apply_watermark": False,
        }
        if isinstance(voice_spec, dict):
            infer_kwargs["use_ref_codes"] = use_ref_codes

        async with self._inference_semaphore:
            wav = await asyncio.to_thread(
                engine.infer,
                **infer_kwargs,
            )

        fd, wav_path_str = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        wav_path = Path(wav_path_str)
        try:
            await asyncio.to_thread(engine.save, wav, wav_path)
            mp3_path = wav_path.with_suffix(".mp3")
            command = [
                settings.ffmpeg_binary_path,
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
                raw_response={"engine": "vieneu-v3-turbo", "voice": voice_type, "script": True},
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
        options: SynthesisOptions | None = None,
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

        voice_spec, ref_audio, prompt_text, use_ref_codes = await self._resolve_custom_voice(voice_type)

        async def feed_pcm():
            try:
                # The infer_stream method is a generator, so we must advance it in a thread.
                gen = engine.infer_stream(
                    text=text,
                    voice=voice_spec,
                    ref_audio=ref_audio,
                    prompt_text=prompt_text,
                    style=style or "tu_nhien",
                    use_ref_codes=use_ref_codes,
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

    async def _resolve_custom_voice(
        self, voice_type: str
    ) -> tuple[str | dict | None, str | None, str | None, bool]:
        try:
            uuid.UUID(voice_type)
        except ValueError:
            return voice_type, None, None, True

        from app.services.voice_resolver import resolve_voice

        try:
            async with AsyncSessionLocal() as session:
                resolved = await resolve_voice(session, voice_type)
                if resolved:
                    if resolved.speaker_emb is not None:
                        # V2 enrolled voice: zero prepare_reference in synthesis!
                        use_ref = (resolved.clone_mode == "fidelity")
                        voice_spec = {
                            "speaker_emb": resolved.speaker_emb,
                            "codes": resolved.ref_codes,
                        }
                        return voice_spec, None, resolved.prompt_text, use_ref
                    if resolved.reference_audio_path:
                        # V1 fallback
                        return None, resolved.reference_audio_path, resolved.prompt_text, True
        except Exception:
            logger.debug("Failed resolving voice %s via resolver, fallback to type", voice_type)

        return voice_type, None, None, True
