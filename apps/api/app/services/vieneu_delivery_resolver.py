"""Resolve Void Melody delivery intent into safe VieNeu v3 Turbo input."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.schemas.emotional_script import DeliveryIntent, ScriptLine
from app.services.global_delivery_interpreter import GlobalDeliveryResolution

NATIVE_CUES = {
    "laugh": "[cười]",
    "sigh": "[thở dài]",
    "clear_throat": "[hắng giọng]",
}
APPROXIMATED_INTENTS = {
    DeliveryIntent.CALM.value,
    DeliveryIntent.JOY.value,
    DeliveryIntent.SAD.value,
    DeliveryIntent.FEAR.value,
    DeliveryIntent.ANGER.value,
    DeliveryIntent.SURPRISE.value,
    DeliveryIntent.TENSION.value,
    DeliveryIntent.MYSTERIOUS.value,
    DeliveryIntent.NARRATION.value,
    DeliveryIntent.SHOUT.value,
}


@dataclass(frozen=True)
class ResolvedVieNeuDelivery:
    voice_id: str
    voice_mode: str
    text: str
    emitted_text: str
    native_cues: list[str]
    approximated_intents: list[str]
    unsupported_intents: list[str]
    rate: float
    pause_before_ms: int
    pause_after_ms: int
    warnings: list[str]
    synthesis_options: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def resolve_vieneu_delivery(
    line: ScriptLine,
    *,
    voice_id: str,
    voice_mode: str,
    global_delivery: GlobalDeliveryResolution | None = None,
    base_rate: float = 1.0,
) -> ResolvedVieNeuDelivery:
    instruction = line.delivery
    intent = instruction.intent.value
    native_cues = [event.value for event in instruction.nonverbals]
    prefix = " ".join(NATIVE_CUES[event] for event in native_cues)
    emitted_text = f"{prefix} {line.text}".strip()

    approximated = [intent] if intent in APPROXIMATED_INTENTS else []
    unsupported = [intent] if intent == DeliveryIntent.WHISPER.value else []
    if unsupported:
        approximated = []

    pace = global_delivery.pace if global_delivery else "normal"
    rate = base_rate
    if pace == "slow":
        rate *= 0.95
    elif pace == "fast":
        rate *= 1.05
    if intent in {DeliveryIntent.FEAR.value, DeliveryIntent.TENSION.value}:
        rate *= 0.98
    rate = max(0.5, min(2.0, round(rate, 3)))

    pause_before = instruction.pause_before_ms
    pause_after = instruction.pause_after_ms
    if intent in {DeliveryIntent.FEAR.value, DeliveryIntent.TENSION.value, DeliveryIntent.MYSTERIOUS.value}:
        pause_after += int(250 + instruction.intensity * 250)
    if global_delivery and global_delivery.pause_density == "high":
        pause_after += 150
    elif global_delivery and global_delivery.pause_density == "low":
        pause_after = max(0, pause_after - 100)

    warnings: list[str] = []
    if unsupported:
        warnings.append("Whisper is not a native VieNeu control and was not synthesized as a fake style.")
    if approximated and voice_mode == "CLONE":
        warnings.append("Emotion is approximated for VieNeu clone voice and depends on reference audio.")
    if approximated and voice_mode != "CLONE":
        warnings.append("Emotion is approximated for VieNeu preset voice.")
    if global_delivery and global_delivery.unsupported_hints:
        warnings.extend(f"Global delivery hint is metadata only: {hint}." for hint in global_delivery.unsupported_hints)

    return ResolvedVieNeuDelivery(
        voice_id=voice_id,
        voice_mode=voice_mode,
        text=line.text,
        emitted_text=emitted_text,
        native_cues=native_cues,
        approximated_intents=approximated,
        unsupported_intents=unsupported,
        rate=rate,
        pause_before_ms=pause_before,
        pause_after_ms=pause_after,
        warnings=warnings,
        synthesis_options={},
    )

