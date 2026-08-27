"""OmniVoice TTS provider adapter.

Routes all OmniVoice inference through the isolated OmniVoiceRuntimeClient.
Never imports torch / omnivoice / transformers into the core API process.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.omnivoice_voice import OmniVoiceVoiceModel
from app.providers.base import ProviderResult, ProviderVoice, SynthesisOptions
from app.providers.registry import OMNIVOICE
from app.services.omnivoice_model_service import (
    OmniVoiceModelError,
    omnivoice_model_service,
)
from app.services.omnivoice_runtime import (
    OmniSynthesisRequest,
    OmniVoiceRuntimeClient,
    OmniVoiceRuntimeError,
)
from app.services.omnivoice_voice_resolver import (
    OmniVoiceResolutionError,
    resolve_omnivoice_voice,
)

logger = logging.getLogger(__name__)


class OmniVoiceProvider:
    """Provider adapter for OmniVoice / G-OmniVoice voice design and synthesis."""

    provider_id = OMNIVOICE
    default_sample_rate = 24000
    default_mime_type = "audio/wav"

    def __init__(
        self,
        *,
        runtime_client: OmniVoiceRuntimeClient | None = None,
    ) -> None:
        self._runtime = runtime_client or OmniVoiceRuntimeClient(
            default_timeout_seconds=settings.omnivoice_inference_timeout_seconds,
        )

    async def list_voices(self, language: str | None = None) -> list[ProviderVoice]:
        """Return saved OmniVoice voices as provider voices."""
        async with AsyncSessionLocal() as session:
            stmt = select(OmniVoiceVoiceModel).where(
                OmniVoiceVoiceModel.status == "ready"
            )
            voices = list(await session.scalars(stmt))

        result: list[ProviderVoice] = []
        for voice in voices:
            result.append(
                ProviderVoice(
                    language_short=language[:2] if language else "vi",
                    language_code=language or "vi-VN",
                    voice_type=voice.id,
                    display_name=voice.display_name,
                    resource_id=None,
                    provider_id=OMNIVOICE,
                    gender=None,
                    region=None,
                    style="voice-design",
                    description=voice.compiled_instruction or voice.design_prompt,
                )
            )
        return result

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
        """Synthesize *text* using a saved OmniVoice VoiceClonePrompt.

        Raises:
            OmniVoiceResolutionError: if voice_id cannot be resolved.
            OmniVoiceRuntimeError: if the worker process fails.
            OmniVoiceModelError: if the model is not installed.
        """
        async with AsyncSessionLocal() as session:
            resolved = await resolve_omnivoice_voice(session, voice_type)

        return await self._synthesize_with_prompt(
            text=text,
            prompt_artifact_path=Path(resolved.prompt_artifact_path),
            output_voice_type=voice_type,
            engine_id=resolved.engine_id,
            model_revision=resolved.model_revision,
            rate=rate,
            options=options,
            destination_path=destination_path,
        )

    async def synthesize_preview(
        self,
        *,
        text: str,
        instruction: str,
        language: str | None = None,
        rate: float = 1.0,
        destination_path: Path | None = None,
    ) -> ProviderResult:
        """Synthesize a preview candidate directly from a design instruction.

        This does not require a saved VoiceClonePrompt; it uses the runtime's
        instruction-conditioned synthesis path for design exploration.
        """
        return await self._synthesize_with_prompt(
            text=text,
            prompt_artifact_path=None,
            output_voice_type="__voice_design__",
            engine_id="g-omnivoice",
            model_revision=None,
            rate=rate,
            options=SynthesisOptions(
                language=language,
                instruction=instruction,
            ),
            destination_path=destination_path,
        )

    async def _synthesize_with_prompt(
        self,
        *,
        text: str,
        prompt_artifact_path: Path | None,
        output_voice_type: str,
        engine_id: str,
        model_revision: str | None,
        rate: float = 1.0,
        options: SynthesisOptions | None = None,
        destination_path: Path | None = None,
    ) -> ProviderResult:
        """Shared implementation for saved-voice and preview synthesis."""
        self._ensure_model_loaded()

        if destination_path is None:
            destination_path = self._temp_output_path()
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        request = OmniSynthesisRequest(
            text=text,
            output_path=str(destination_path),
            language=(options.language if options else None),
            instruction=(options.instruction if options else None),
            voice_prompt_path=str(prompt_artifact_path) if prompt_artifact_path else None,
            duration=(options.target_duration_seconds if options else None),
            speed=rate,
            normalize_text=(options.normalize_text if options else False),
        )

        try:
            result = await self._runtime.synthesize(
                request,
                timeout_seconds=settings.omnivoice_inference_timeout_seconds,
            )
        except OmniVoiceRuntimeError:
            raise
        except Exception as exc:
            raise OmniVoiceRuntimeError(
                "OMNI_RUNTIME_BROKEN",
                f"Unexpected OmniVoice runtime failure: {exc}",
            ) from exc

        return ProviderResult(
            raw_response={
                "provider_id": OMNIVOICE,
                "engine_id": engine_id,
                "voice_type": output_voice_type,
                "model_revision": model_revision,
                "sample_rate": result.sample_rate,
            },
            audio_urls=[],
            local_paths=[str(Path(result.output_path))],
            mime_type=self.default_mime_type,
            sample_rate=result.sample_rate or self.default_sample_rate,
        )

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
        """Streaming synthesis is not implemented for OmniVoice V1."""
        raise NotImplementedError("OmniVoice streaming synthesis is not implemented.")

    async def preflight_voice_prompt(self, prompt_path: Path) -> None:
        """Validate a VoiceClonePrompt artifact without synthesizing."""
        await self._runtime.validate_voice_prompt(str(prompt_path))

    def _ensure_model_loaded(self) -> Path:
        """Return the managed G-OmniVoice model path, loading it if necessary.

        This is a core-side coordinator call; the actual model lives in the
        worker process. We check local snapshot presence and then ask the worker
        to load it.
        """
        try:
            model_path = omnivoice_model_service.resolve_model_path()
        except OmniVoiceModelError as exc:
            raise OmniVoiceResolutionError(
                exc.code,
                exc.message,
            ) from exc

        return model_path

    def _temp_output_path(self) -> Path:
        return settings.audio_storage_dir / f"omnivoice_{id(self)}_{OmniVoiceRuntimeClient.__name__}.wav"


async def _resolve_voice_for_provider(
    session: AsyncSession,
    voice_id: str,
) -> dict[str, Any]:
    """Lightweight resolver used when provider itself needs voice metadata."""
    try:
        resolved = await resolve_omnivoice_voice(session, voice_id)
        return resolved.to_dict()
    except OmniVoiceResolutionError as exc:
        logger.warning("OmniVoice voice resolution failed: %s", exc.message)
        raise
