from app.schemas.emotional_script import (
    DeliveryInstruction,
    ScriptLine,
)
from app.services.vieneu_delivery_resolver import (
    resolve_vieneu_delivery,
)


def _line(*, intent: str = "neutral", nonverbals: list[str] | None = None) -> ScriptLine:
    return ScriptLine(
        id="line-1-1",
        order=0,
        text="Anh có nghe thấy gì không?",
        delivery=DeliveryInstruction(
            intent=intent,
            intensity=0.8,
            nonverbals=nonverbals or [],
        ),
    )


def test_native_cues_are_emitted_only_at_final_vieneu_text_layer():
    resolved = resolve_vieneu_delivery(
        _line(nonverbals=["laugh", "sigh", "clear_throat"]),
        voice_id="preset-1",
        voice_mode="PRESET",
    )

    assert resolved.emitted_text == "[cười] [thở dài] [hắng giọng] Anh có nghe thấy gì không?"
    assert resolved.native_cues == ["laugh", "sigh", "clear_throat"]
    assert resolved.approximated_intents == []
    assert "style" not in resolved.synthesis_options


def test_non_native_clone_delivery_is_safe_approximation_and_is_labeled():
    resolved = resolve_vieneu_delivery(
        _line(intent="fear"),
        voice_id="clone-1",
        voice_mode="CLONE",
    )

    assert "[sợ hãi]" not in resolved.emitted_text
    assert resolved.approximated_intents == ["fear"]
    assert resolved.pause_after_ms > 0
    assert resolved.warnings == [
        "Emotion is approximated for VieNeu clone voice and depends on reference audio."
    ]


def test_whisper_is_unsupported_without_faking_a_model_control():
    resolved = resolve_vieneu_delivery(
        _line(intent="whisper"),
        voice_id="preset-1",
        voice_mode="PRESET",
    )

    assert resolved.unsupported_intents == ["whisper"]
    assert resolved.emitted_text == "Anh có nghe thấy gì không?"
    assert resolved.synthesis_options == {}

