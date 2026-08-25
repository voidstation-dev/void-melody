"""Runtime PreparedVoice abstraction for reusing resolved preset and enrolled v2 voice artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PreparedVoice:
    """Runtime-only immutable snapshot of a resolved voice profile."""

    voice_type: str
    provider_id: str
    source: str  # "preset" | "custom"
    voice_revision: str

    speaker_emb: np.ndarray | None = None
    ref_codes: np.ndarray | None = None
    clone_mode: str = "fidelity"
    profile_format_version: str = "reference-v1"

    reference_audio_path: str | None = None
    prompt_text: str | None = None

    @property
    def is_enrollment_v2(self) -> bool:
        return (
            self.source == "custom"
            and self.speaker_emb is not None
            and self.ref_codes is not None
            and self.profile_format_version == "vieneu-enrollment-v2"
        )

    def to_vieneu_voice_spec(self) -> dict[str, Any] | str:
        """Convert to the voice parameter expected by Vieneu.infer / infer_batch."""
        if self.source == "preset":
            return self.voice_type
        if self.is_enrollment_v2:
            return {
                "speaker_emb": self.speaker_emb,
                "codes": self.ref_codes,
            }
        return self.voice_type
