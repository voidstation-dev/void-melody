from pathlib import Path

from app.services.script_audio_composer import CompositionSegment, build_composition_command


def test_composition_command_uses_canonical_mono_48khz_and_pause_inputs():
    command = build_composition_command(
        segments=[
            CompositionSegment(Path("one.mp3"), pause_before_ms=200, pause_after_ms=400),
            CompositionSegment(Path("two.mp3")),
        ],
        destination=Path("output.mp3"),
        output_format="mp3",
        ffmpeg_binary="ffmpeg",
    )

    assert "-ar" in command
    assert "48000" in command
    assert "-ac" in command
    assert "1" in command
    assert "anullsrc=r=48000:cl=mono:d=0.2" in command
    assert "anullsrc=r=48000:cl=mono:d=0.4" in command
    assert str(Path("output.tmp.mp3")) in command
