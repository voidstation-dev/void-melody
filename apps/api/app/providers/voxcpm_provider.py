"""VoxCPM2 TTS provider adapter.

Routes all VoxCPM2 inference through the isolated VoxCpmRuntimeClient
(apps/voxcpm-worker via JSONL IPC). Never imports torch / voxcpm into the
core API process, never calls VieneuProvider, and has no fallback to any
other provider — VoxCPM2 jobs either succeed via the VoxCPM2 runtime or
fail explicitly.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.voxcpm_voice import VoxCpmVoiceModel
from app.providers.base import ProviderResult, ProviderVoice, SynthesisOptions
from app.providers.registry import VOXCPM2
from app.services.voxcpm_runtime import (
    VoxCpmRuntimeClient,
    VoxCpmRuntimeError,
    VoxCpmSynthesisRequest,
)
from app.services.speech_runtime_coordinator import (
    SpeechRuntimeCoordinatorError,
    speech_runtime_coordinator,
)

logger = logging.getLogger(__name__)

DEFAULT_VOXCPM_MODEL_ID = "openbmb/VoxCPM2"


class VoxCpmProviderError(Exception):
    """Explicit failure raised by the VoxCPM2 provider (no silent fallback)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class VoxCpmProvider:
    """Provider adapter for VoxCPM2 cloned-voice synthesis.

    Voice identity = reference audio saved on the cloned voice; performance =
    emotion preset (carried in the job ``style`` column) or explicit
    instruction (``options.instruction``).
    """

    provider_id = VOXCPM2
    default_sample_rate = 48000
    default_mime_type = "audio/wav"

    def __init__(
        self,
        *,
        runtime_client: VoxCpmRuntimeClient | None = None,
    ) -> None:
        # Lazy client: constructing a real VoxCpmRuntimeClient requires the
        # dedicated worker env, which must not break scheduler startup when
        # VoxCPM2 is not installed.
        self._runtime: VoxCpmRuntimeClient | None = runtime_client
        self._loaded_model_id: str | None = None
        # Phase 9: register with the speech runtime coordinator so a VoxCPM2
        # model load can request an unload of other heavy runtimes first
        # (VieNeu keeps its own governor; VoxCPM2 is NOT inside it).
        speech_runtime_coordinator.register(
            VOXCPM2,
            unload=self.unload_model,
            is_loaded=lambda: self._loaded_model_id is not None,
            label="VoxCPM2",
        )

    async def list_voices(self, language: str | None = None) -> list[ProviderVoice]:
        """Return saved VoxCPM2 cloned voices as provider voices."""
        async with AsyncSessionLocal() as session:
            stmt = select(VoxCpmVoiceModel).where(VoxCpmVoiceModel.status == "ready")
            voices = list(await session.scalars(stmt))

        return [
            ProviderVoice(
                language_short=language[:2] if language else "vi",
                language_code=language or "vi-VN",
                voice_type=voice.id,
                display_name=voice.display_name,
                resource_id=None,
                provider_id=VOXCPM2,
                gender=None,
                region=None,
                style="cloned",
                description=voice.description,
            )
            for voice in voices
        ]

    async def synthesize(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None = None,
        rate: float = 1.0,
        style: str | None = None,
        options: SynthesisOptions | None = None,
        destination_path: Path | None = None,
    ) -> ProviderResult:
        """Synthesize *text* with a saved VoxCPM2 cloned voice.

        Raises:
            VoxCpmProviderError: if the voice cannot be resolved.
            VoxCpmRuntimeError: if the worker process fails.
        """
        async with AsyncSessionLocal() as session:
            voice = await session.get(VoxCpmVoiceModel, voice_type)
        if voice is None:
            raise VoxCpmProviderError(
                "VOXCPM_VOICE_NOT_FOUND",
                f"VoxCPM2 voice '{voice_type}' does not exist.",
            )
        if voice.status != "ready":
            raise VoxCpmProviderError(
                "VOXCPM_VOICE_NOT_READY",
                "Selected VoxCPM2 voice is not ready for synthesis.",
            )
        if (
            not voice.reference_audio_path
            or not Path(voice.reference_audio_path).is_file()
        ):
            raise VoxCpmProviderError(
                "VOXCPM_REFERENCE_MISSING",
                "Selected VoxCPM2 voice reference audio is missing.",
            )

        if destination_path is None:
            destination_path = (
                settings.audio_storage_dir / f"voxcpm2_{voice_type}.wav"
            )
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        emotion = (style or "").strip() or None
        instruction = (options.instruction if options else None) or None
        if emotion and instruction:
            raise VoxCpmProviderError(
                "VOXCPM_INVALID_PARAMS",
                "Provide either an emotion preset (style) or an explicit "
                "instruction, not both.",
            )

        request = VoxCpmSynthesisRequest(
            text=text,
            output_path=str(destination_path),
            reference_wav_path=voice.reference_audio_path,
            instruction=instruction,
            emotion=emotion,
        )

        try:
            result = await self._synthesize_with_runtime(
                request, model_id=voice.model_id or DEFAULT_VOXCPM_MODEL_ID
            )
        except VoxCpmRuntimeError:
            raise
        except VoxCpmProviderError:
            raise
        except Exception as exc:
            raise VoxCpmProviderError(
                "VOXCPM_RUNTIME_BROKEN",
                f"Unexpected VoxCPM2 runtime failure: {exc}",
            ) from exc

        return ProviderResult(
            raw_response={
                "provider_id": VOXCPM2,
                "voice_type": voice_type,
                "model_id": voice.model_id or DEFAULT_VOXCPM_MODEL_ID,
                "sample_rate": result.sample_rate,
                "method": result.method,
            },
            audio_urls=[],
            local_paths=[str(Path(result.output_path))],
            mime_type=self.default_mime_type,
            sample_rate=result.sample_rate or self.default_sample_rate,
        )

    async def _synthesize_with_runtime(
        self,
        request: VoxCpmSynthesisRequest,
        *,
        model_id: str,
    ):
        client = self._get_runtime()
        try:
            await self._ensure_model_loaded(client, model_id)
            # Emotional path is always used: neutral (no emotion/instruction)
            # compiles to the plain text inside the worker.
            return await client.synthesize(
                request,
                method="synthesize_emotional",
                timeout_seconds=settings.voxcpm_inference_timeout_seconds,
            )
        except VoxCpmRuntimeError as exc:
            if exc.code in ("VOXCPM_RUNTIME_CRASHED", "VOXCPM_RUNTIME_TIMEOUT"):
                # Worker generation is dead — force a fresh client next call.
                await self._reset_runtime()
            raise
        except SpeechRuntimeCoordinatorError:
            # Explicit failure: another heavy runtime refused to unload.
            # No silent fallback — surface to the job error path.
            raise VoxCpmProviderError(
                "VOXCPM_RUNTIME_BUSY",
                "Another heavy speech runtime is active and could not be "
                "unloaded. Retry after switching engines in Settings.",
            )

    def _get_runtime(self) -> VoxCpmRuntimeClient:
        if self._runtime is None:
            self._runtime = VoxCpmRuntimeClient(
                mock_mode=False,
                default_timeout_seconds=settings.voxcpm_inference_timeout_seconds,
            )
            self._loaded_model_id = None
        return self._runtime

    async def _ensure_model_loaded(
        self, client: VoxCpmRuntimeClient, model_id: str
    ) -> None:
        if self._loaded_model_id == model_id and client.is_running:
            return
        # Phase 9: request an unload of other heavy speech runtimes before
        # loading. Fails explicitly (no silent fallback) if unload fails.
        await speech_runtime_coordinator.acquire_exclusive(VOXCPM2)
        await client.load_model(model_id, device="auto")
        self._loaded_model_id = model_id

    async def _reset_runtime(self) -> None:
        client = self._runtime
        self._runtime = None
        self._loaded_model_id = None
        if client is not None:
            try:
                await client.shutdown()
            except Exception:  # noqa: BLE001 - shutdown best effort
                logger.debug("VoxCPM2 runtime shutdown during reset failed", exc_info=True)

    async def synthesize_stream(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None = None,
        rate: float = 1.0,
        style: str | None = None,
        options: SynthesisOptions | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Streaming synthesis is not implemented for VoxCPM2 MVP."""
        raise NotImplementedError("VoxCPM2 streaming synthesis is not implemented.")

    async def unload_model(self) -> dict:
        """Explicit model unload — must be reliable even when the worker is
        already dead (Phase 9 exit criterion)."""
        client = self._runtime
        self._loaded_model_id = None
        if client is None:
            return {"status": "not_running", "released": False}
        try:
            result = await client.unload_model()
        except Exception as exc:  # noqa: BLE001 - unload reliability: a dead
            # worker already released its memory; report that honestly.
            logger.info(
                "VoxCPM2 unload RPC failed (worker likely dead): %s", exc
            )
            return {"status": "released", "released": True, "note": str(exc)}
        finally:
            await self._reset_runtime()
        return result