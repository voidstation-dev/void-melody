import json
import threading
from pathlib import Path

from app.config import settings
from app.providers.base import ProviderVoice
from app.services.vieneu_preset_catalog import list_vieneu_preset_voices


class VoiceCatalog:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._mtime_ns: int | None = None
        self._voices: tuple[ProviderVoice, ...] = ()
        self._by_voice_type: dict[str, ProviderVoice] = {}

    def _refresh_if_changed(self) -> None:
        try:
            mtime_ns = self.path.stat().st_mtime_ns
        except FileNotFoundError:
            with self._lock:
                self._mtime_ns = None
                self._voices = ()
                self._by_voice_type = {}
            return

        with self._lock:
            if self._mtime_ns == mtime_ns:
                return

            payload = json.loads(self.path.read_text(encoding="utf-8"))
            voices: list[ProviderVoice] = []
            for item in payload:
                voice_type = item.get("voice_type", "")
                if not voice_type or "Neural" in voice_type:
                    continue
                voices.append(
                    ProviderVoice(
                        language_short=item.get("lan", ""),
                        language_code=item.get("lang", ""),
                        voice_type=voice_type,
                        display_name=item.get("display_name", ""),
                        resource_id=item.get("resource_id", ""),
                        captured_at=item.get("captured_at"),
                    )
                )

            voices.extend(list_vieneu_preset_voices())

            self._voices = tuple(voices)
            self._by_voice_type = {voice.voice_type: voice for voice in voices}
            self._mtime_ns = mtime_ns

    def get_voice(self, voice_type: str) -> ProviderVoice | None:
        self._refresh_if_changed()
        return self._by_voice_type.get(voice_type)

    def list_voices(self, language: str | None = None) -> list[ProviderVoice]:
        self._refresh_if_changed()
        if language is None:
            return list(self._voices)
        language_lower = language.lower()
        return [
            voice
            for voice in self._voices
            if voice.language_code.lower() == language_lower
        ]


voice_catalog = VoiceCatalog(settings.capcut_catalog_path)
