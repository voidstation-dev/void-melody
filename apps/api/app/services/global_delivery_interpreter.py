"""Deterministic interpretation of the user-facing global delivery prompt."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GlobalDeliveryResolution:
    pace: str = "normal"
    pause_density: str = "normal"
    mood_hint: str | None = None
    unsupported_hints: tuple[str, ...] = ()


def interpret_global_delivery(prompt: str | None) -> GlobalDeliveryResolution:
    value = (prompt or "").strip().lower()
    if not value:
        return GlobalDeliveryResolution()

    pace = "normal"
    if any(token in value for token in ("chậm", "chậm rãi", "slow")):
        pace = "slow"
    elif any(token in value for token in ("nhanh", "fast")):
        pace = "fast"

    pause_density = "normal"
    if "nhiều khoảng nghỉ" in value or "more pauses" in value:
        pause_density = "high"
    elif "ít khoảng nghỉ" in value or "fewer pauses" in value:
        pause_density = "low"

    mood_hint = next(
        (
            mood
            for tokens, mood in (
                (("bí ẩn", "mysterious"), "mysterious"),
                (("bi thương", "tragic"), "sad"),
                (("căng thẳng", "tension"), "tension"),
                (("vui", "joyful"), "joy"),
            )
            if any(token in value for token in tokens)
        ),
        None,
    )

    unsupported = []
    for hint in ("giọng trầm", "deep voice", "bi tráng", "tragic timbre"):
        if hint in value:
            unsupported.append(hint)

    return GlobalDeliveryResolution(
        pace=pace,
        pause_density=pause_density,
        mood_hint=mood_hint,
        unsupported_hints=tuple(unsupported),
    )

