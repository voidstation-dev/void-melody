from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any

from capcut_tts_api import CapCutClient

from app.providers.base import ProviderResult, ProviderVoice, SynthesisOptions
from app.services.provider_circuit_breaker import ProviderCircuitBreaker
from app.services.provider_response_parser import extract_audio_urls
from app.services.retry_policy import map_provider_error
from app.services.voice_catalog import VoiceCatalog


class CapCutProvider:
    def __init__(
        self,
        *,
        catalog_path: Path,
        device_path: Path | None = None,
        timeout_seconds: float = 90.0,
        client_factory: Callable[[Path | None], Any] | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
    ):
        self.catalog = VoiceCatalog(catalog_path)
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker = circuit_breaker
        factory = client_factory or self._create_client
        self.client = factory(device_path)

    @staticmethod
    def _create_client(device_path: Path | None) -> CapCutClient:
        if device_path is None:
            return CapCutClient()
        return CapCutClient(device=device_path)

    async def list_voices(self, language: str | None = None) -> list[ProviderVoice]:
        return self.catalog.list_voices(language)

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
        **kwargs: Any,
    ) -> ProviderResult:
        import asyncio

        if self.circuit_breaker is not None:
            self.circuit_breaker.before_call()
        try:
            response = await asyncio.to_thread(
                self.client.generate_speech,
                texts=text,
                voice=voice_type,
                resource_id=resource_id,
                rate=f"{rate:.2f}",
                wait=True,
                poll_interval=1.0,
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            error = map_provider_error(exc)
            if self.circuit_breaker is not None:
                self.circuit_breaker.record_failure(error)
            raise error from exc

        if self.circuit_breaker is not None:
            self.circuit_breaker.record_success()
        return ProviderResult(
            raw_response=response,
            audio_urls=extract_audio_urls(response),
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
        destination_path: Path | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[bytes, None]:
        import httpx

        from app.exceptions import TTSJobError

        result = await self.synthesize(
            text=text,
            voice_type=voice_type,
            resource_id=resource_id,
            rate=rate,
            style=style,
            options=options,
        )
        if not result.audio_urls:
            raise TTSJobError(
                code="AUDIO_URL_NOT_FOUND",
                message="CapCut did not return an audio URL",
                retryable=False,
            )

        url = result.audio_urls[0]
        async with (
            httpx.AsyncClient(timeout=30.0) as client,
            client.stream("GET", url) as response,
        ):
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=8192):
                yield chunk
