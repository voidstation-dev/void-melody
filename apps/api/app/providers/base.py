from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderVoice:
    language_short: str
    language_code: str
    voice_type: str
    display_name: str
    resource_id: str | None = None
    captured_at: str | None = None
    provider_id: str = "capcut"
    gender: str | None = None
    region: str | None = None
    style: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class SynthesisOptions:
    language: str | None = None
    instruction: str | None = None
    target_duration_seconds: float | None = None
    normalize_text: bool = False


@dataclass(frozen=True)
class ProviderResult:
    raw_response: dict[str, Any]
    audio_urls: list[str]
    local_paths: list[str] | None = None


class TTSProvider(Protocol):
    async def list_voices(self, language: str | None = None) -> list[ProviderVoice]: ...
    async def synthesize(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None,
        rate: float,
        style: str | None = None,
        options: SynthesisOptions | None = None,
    ) -> ProviderResult: ...
    async def synthesize_stream(
        self,
        *,
        text: str,
        voice_type: str,
        resource_id: str | None,
        rate: float,
        style: str | None = None,
        options: SynthesisOptions | None = None,
    ) -> AsyncGenerator[bytes, None]: ...
