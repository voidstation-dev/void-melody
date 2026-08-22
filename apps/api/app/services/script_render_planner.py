"""Pure render planning and cache fingerprint helpers."""

from __future__ import annotations

import hashlib
import json

from app.schemas.emotional_script import ScriptLine
from app.services.global_delivery_interpreter import GlobalDeliveryResolution
from app.services.vieneu_delivery_resolver import resolve_vieneu_delivery


def compute_segment_fingerprint(
    *,
    line: ScriptLine,
    voice_id: str,
    voice_mode: str,
    voice_revision: str | None = None,
    global_delivery: GlobalDeliveryResolution | None = None,
    base_rate: float = 1.0,
) -> str:
    resolved = resolve_vieneu_delivery(
        line,
        voice_id=voice_id,
        voice_mode=voice_mode,
        global_delivery=global_delivery,
        base_rate=base_rate,
    )
    payload = {
        "engine": "vieneu-v3-turbo",
        "voice_id": voice_id,
        "voice_mode": voice_mode,
        "voice_revision": voice_revision or "unknown",
        "resolved": resolved.as_dict(),
        "line": line.model_dump(mode="json"),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

