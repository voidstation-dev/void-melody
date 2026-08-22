"""Thin Emotional Script adapter over the existing VieNeu runtime."""

from __future__ import annotations

from typing import Any

from app.exceptions import TTSJobError
from app.providers.base import ProviderResult
from app.services.vieneu_delivery_resolver import ResolvedVieNeuDelivery


class VieNeuScriptSynthesisAdapter:
    def __init__(self, *, provider: Any) -> None:
        self.provider = provider

    async def synthesize(self, resolved: ResolvedVieNeuDelivery) -> ProviderResult:
        method = getattr(self.provider, "synthesize_script", None)
        if not callable(method):
            raise TTSJobError(
                code="VIENEU_RUNTIME_UNAVAILABLE",
                message="VieNeu runtime does not expose the script synthesis adapter.",
                retryable=True,
            )
        result = await method(
            text=resolved.emitted_text,
            voice_type=resolved.voice_id,
            rate=resolved.rate,
        )
        if not result.audio_urls and not result.local_paths:
            raise TTSJobError(
                code="AUDIO_INVALID",
                message="VieNeu returned no audio artifact.",
                retryable=False,
            )
        return result

