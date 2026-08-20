"""Unit tests for vieneu-core contracts, capabilities, errors, and fixtures.

These tests import only the standard library + vieneu_core itself — no numpy,
no VieNeu engine, no FastAPI. They verify the stable surface is well-formed
and that fixtures are deterministic.
"""

import dataclasses
import struct

import pytest

from vieneu_core import (
    AudioFormat,
    Capabilities,
    InvalidStyleError,
    InvalidTextError,
    ModelNotAvailableError,
    Style,
    SynthesizeResult,
    Voice,
    VoiceNotFoundError,
    default_capabilities,
    default_descriptor,
)
from vieneu_core.capabilities import capabilities_for_runtime
from vieneu_core.engine import RuntimeProbe
from vieneu_core.fixtures import (
    FIXTURE_STYLES,
    FIXTURE_VOICES,
    make_capabilities,
    make_synthesize_request,
)


def test_contracts_are_frozen():
    voice = FIXTURE_VOICES[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        voice.voice_id = "other"  # type: ignore[misc]
    style = FIXTURE_STYLES[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        style.id = "other"  # type: ignore[misc]


def test_audio_format_values():
    assert AudioFormat.WAV.value == "wav"
    assert AudioFormat.MP3.value == "mp3"
    assert AudioFormat.M4A.value == "m4a"


def test_default_capabilities_match_v3_turbo_survey():
    caps = default_capabilities()
    assert caps.supports_preset_voices is True
    assert caps.supports_voice_cloning is True
    assert caps.supports_streaming is True
    assert caps.supports_styles is True
    assert caps.supports_batch is True
    assert caps.supports_emotion_tags is True
    assert caps.sample_rate == 48000
    assert caps.max_text_chars == 256


def test_default_descriptor_ids():
    desc = default_descriptor()
    assert desc.id == "vieneu"
    assert desc.label == "VieNeu"
    assert isinstance(desc.capabilities, Capabilities)


def test_fixture_styles_match_known_set():
    ids = {s.id for s in FIXTURE_STYLES}
    assert ids == {"tu_nhien", "tin_tuc", "doc_truyen"}
    assert all(s.token_id is not None for s in FIXTURE_STYLES)


def test_fixture_voices_are_preset_and_deterministic():
    assert len(FIXTURE_VOICES) == 3
    assert all(v.source == "preset" for v in FIXTURE_VOICES)
    assert FIXTURE_VOICES[0].voice_id == "Minh Đức"
    # Re-importing should yield identical objects (deterministic).
    from vieneu_core.fixtures import FIXTURE_VOICES as again

    assert again == FIXTURE_VOICES


def test_make_synthesize_request_defaults_and_overrides():
    req = make_synthesize_request()
    assert req.voice_id == "Minh Đức"
    assert req.rate == 1.0
    assert req.ref_audio_path is None
    req2 = make_synthesize_request(voice_id="Trúc Ly", rate=1.5, style="doc_truyen")
    assert req2.voice_id == "Trúc Ly"
    assert req2.rate == 1.5
    assert req2.style == "doc_truyen"


def test_make_capabilities_overrides():
    caps = make_capabilities(supports_streaming=False, sample_rate=24000)
    assert caps.supports_streaming is False
    assert caps.sample_rate == 24000


def test_cpu_onnx_runtime_supports_zero_shot_clone_and_denoise():
    probe = RuntimeProbe(
        device="cpu",
        backend="onnx",
        onnxruntime_available=True,
        torch_available=False,
        torch_cuda_available=False,
        cpu_count=8,
        threads=0,
        platform="test",
    )

    capabilities = capabilities_for_runtime(probe, engine_version="3.2.4")

    assert capabilities.supports_preset_voices is True
    assert capabilities.supports_voice_cloning is True
    assert capabilities.supports_denoise is True
    assert capabilities.supports_streaming is True
    assert capabilities.reason_code is None


def test_missing_runtime_disables_clone_without_disabling_contract_shape():
    probe = RuntimeProbe(
        device="cpu",
        backend="onnx",
        onnxruntime_available=False,
        torch_available=False,
        torch_cuda_available=False,
        cpu_count=8,
        threads=0,
        platform="test",
    )

    capabilities = capabilities_for_runtime(probe, engine_version="3.2.4")

    assert capabilities.supports_preset_voices is False
    assert capabilities.supports_voice_cloning is False
    assert capabilities.supports_denoise is False
    assert capabilities.reason_code == "RUNTIME_UNAVAILABLE"


def test_synthesize_result_pcm_roundtrip():
    # Simulate the engine producing raw float32 PCM bytes.
    samples = struct.pack("<3f", 0.0, 0.5, -0.5)
    result = SynthesizeResult(pcm_bytes=samples, sample_rate=48000)
    assert result.dtype == "float32"
    assert len(result.pcm_bytes) == 12
    floats = struct.unpack("<3f", result.pcm_bytes)
    assert floats == (0.0, 0.5, -0.5)


def test_error_hierarchy_and_codes():
    err = VoiceNotFoundError(voice_id="missing")
    assert err.code == "VOICE_NOT_FOUND"
    assert err.retryable is False
    assert "missing" in err.message
    assert isinstance(err, Exception)

    style_err = InvalidStyleError(style="bogus")
    assert style_err.code == "INVALID_STYLE"
    assert "bogus" in style_err.message

    text_err = InvalidTextError(message="empty")
    assert text_err.code == "INVALID_TEXT"

    model_err = ModelNotAvailableError()
    assert model_err.code == "MODEL_NOT_AVAILABLE"
    assert model_err.retryable is True


def test_voice_and_style_dataclasses_fields():
    v = Voice(
        voice_id="x",
        display_name="X",
        language_code="vi-VN",
        gender="male",
    )
    assert v.source == "preset"  # default
    s = Style(id="tu_nhien", label="Tự nhiên")
    assert s.token_id is None  # default


def test_synthesize_request_is_frozen():
    req = make_synthesize_request()
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.text = "mutated"  # type: ignore[misc]
