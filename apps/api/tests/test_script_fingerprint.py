from app.schemas.emotional_script import DeliveryInstruction, ScriptLine
from app.services.script_render_planner import compute_segment_fingerprint


def test_fingerprint_changes_when_clone_revision_changes():
    line = ScriptLine(
        id="line-1-1",
        order=0,
        text="Một câu thoại.",
        delivery=DeliveryInstruction(),
    )

    first = compute_segment_fingerprint(
        line=line,
        voice_id="clone-1",
        voice_mode="CLONE",
        voice_revision="rev-a",
    )
    second = compute_segment_fingerprint(
        line=line,
        voice_id="clone-1",
        voice_mode="CLONE",
        voice_revision="rev-b",
    )

    assert first != second
    assert len(first) == 64

