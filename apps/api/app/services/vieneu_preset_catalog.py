"""Load the built-in VieNeu v3 Turbo preset catalog without loading the model."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path

from app.providers.base import ProviderVoice


def _preset_asset_path() -> Path | None:
    spec = find_spec("vieneu")
    if spec is not None:
        package_roots = list(spec.submodule_search_locations or [])
        if spec.origin:
            package_roots.append(str(Path(spec.origin).parent))
        for root in package_roots:
            candidate = Path(root) / "assets" / "voices_v3_turbo.json"
            if candidate.is_file():
                return candidate

    repository_candidate = (
        Path(__file__).resolve().parents[4]
        / "vendor"
        / "vieneu-tts"
        / "src"
        / "vieneu"
        / "assets"
        / "voices_v3_turbo.json"
    )
    return repository_candidate if repository_candidate.is_file() else None


@lru_cache(maxsize=1)
def list_vieneu_preset_voices() -> tuple[ProviderVoice, ...]:
    """Return all named VieNeu presets available in this installation."""

    asset_path = _preset_asset_path()
    payload: dict = {}
    if asset_path is not None:
        try:
            payload = json.loads(asset_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}

    presets = payload.get("presets", {})
    if presets:
        return tuple(
            ProviderVoice(
                language_short="vi",
                language_code="vi-VN",
                voice_type=name,
                display_name=name,
                resource_id=None,
                provider_id="vieneu",
                gender=voice.get("gender"),
                region=voice.get("region"),
                style=voice.get("style"),
                description=voice.get("description"),
            )
            for name, voice in presets.items()
        )

    # Keep development/test installs usable when the optional vendor asset is
    # not present. The full catalog is used whenever the runtime package has it.
    from vieneu_core.fixtures import FIXTURE_VOICES

    return tuple(
        ProviderVoice(
            language_short=voice.language_code.split("-")[0],
            language_code=voice.language_code,
            voice_type=voice.voice_id,
            display_name=voice.display_name,
            resource_id=None,
            provider_id="vieneu",
            gender=voice.gender,
            style=voice.style,
            description=voice.description,
        )
        for voice in FIXTURE_VOICES
    )
