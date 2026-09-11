"""Phase 4 tests: RealVoxCpmBackend behavior without (and with a fake) voxcpm.

The real backend must fail-fast (never fall back to mock), report truthful
runtime info, and support a full neutral synthesis contract against a fake
model object. voxcpm itself requires Python <3.13 + torch, which the FastAPI
test environment does not (and must not) provide.
"""

import sys
import types
import wave
from pathlib import Path

import numpy as np
import pytest

WORKER_DIR = Path(__file__).resolve().parent.parent.parent / "voxcpm-worker"
WORKER_MODULE_NAMES = ("backend", "errors", "path_utils", "mock_backend", "real_backend", "worker")

for _name in WORKER_MODULE_NAMES:
    sys.modules.pop(_name, None)
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

from errors import (  # noqa: E402
    VOXCPM_INVALID_PARAMS,
    VOXCPM_MODEL_NOT_LOADED,
    VOXCPM_PACKAGE_NOT_INSTALLED,
    VOXCPM_REFERENCE_INVALID,
    WorkerError,
)

# errors.py has no VOXCPM_NOT_IMPLEMENTED constant; the backend uses the literal.
VOXCPM_NOT_IMPLEMENTED = "VOXCPM_NOT_IMPLEMENTED"

from real_backend import (  # noqa: E402
    DEFAULT_MODEL_ID,
    DEFAULT_SAMPLE_RATE,
    RealVoxCpmBackend,
    _write_wav_48k,
)


@pytest.fixture(autouse=True)
def _allowed_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("VOID_VOXCPM_ALLOWED_ROOTS", str(tmp_path))
    yield


class FakeTTSModel:
    sample_rate = 48000


class FakeVoxCpmModel:
    tts_model = FakeTTSModel()
    device = "cpu"

    def __init__(self) -> None:
        self.generate_calls: list[dict] = []

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return np.zeros(48000, dtype=np.float32)


def _backend_with_model() -> tuple[RealVoxCpmBackend, FakeVoxCpmModel]:
    backend = RealVoxCpmBackend()
    fake = FakeVoxCpmModel()
    backend.model = fake
    backend.sample_rate = 48000
    return backend, fake


def test_runtime_info_reports_real_without_package():
    backend = RealVoxCpmBackend()
    info = backend.runtime_info()
    assert info["backend"] == "real"
    assert info["package_installed"] is False
    assert info["model_loaded"] is False
    assert info["sample_rate"] == DEFAULT_SAMPLE_RATE
    assert info["model_id"] == DEFAULT_MODEL_ID


def test_load_model_fails_fast_without_package():
    backend = RealVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.load_model({"model_id": DEFAULT_MODEL_ID, "device": "cpu"})
    assert exc_info.value.code == VOXCPM_PACKAGE_NOT_INSTALLED
    assert backend.model is None


def test_load_model_with_fake_package(monkeypatch: pytest.MonkeyPatch):
    """When voxcpm imports cleanly, load_model builds the model via from_pretrained."""

    created_kwargs: dict = {}

    class FakeVoxCPM:
        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs):
            created_kwargs["model_id"] = model_id
            created_kwargs.update(kwargs)
            return FakeVoxCpmModel()

    fake_module = types.ModuleType("voxcpm")
    fake_module.VoxCPM = FakeVoxCPM  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "voxcpm", fake_module)

    backend = RealVoxCpmBackend()
    backend._import_error = None  # simulate a successful import
    result = backend.load_model({"model_id": DEFAULT_MODEL_ID, "device": "auto"})

    assert result["status"] == "loaded"
    assert result["sample_rate"] == 48000
    assert backend.model is not None
    assert created_kwargs["model_id"] == DEFAULT_MODEL_ID
    assert created_kwargs["load_denoiser"] is False  # plan requirement
    # device="auto" must be passed through as "auto" (no forced device kwarg)
    assert "device" not in created_kwargs
    info = backend.runtime_info()
    assert info["package_installed"] is True
    assert info["model_loaded"] is True


def test_unload_releases_model():
    backend, _ = _backend_with_model()
    result = backend.unload_model()
    assert result["status"] == "unloaded"
    assert result["released"] is True
    assert backend.model is None

    # Second unload is a safe no-op reporting released=False
    result2 = backend.unload_model()
    assert result2["released"] is False


def test_synthesis_requires_model(tmp_path: Path):
    backend = RealVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_clone(
            {
                "text": "Xin chào",
                "output_path": str(tmp_path / "out.wav"),
                "reference_wav_path": str(tmp_path / "ref.wav"),
            }
        )
    assert exc_info.value.code == VOXCPM_MODEL_NOT_LOADED


def test_synthesis_requires_text():
    backend, _ = _backend_with_model()
    for bad in ({}, {"text": ""}, {"text": None}):
        with pytest.raises(WorkerError) as exc_info:
            backend.synthesize_clone(bad)
        assert exc_info.value.code == VOXCPM_INVALID_PARAMS


def test_synthesis_requires_reference(tmp_path: Path):
    backend, _ = _backend_with_model()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_clone({"text": "hi", "output_path": str(tmp_path / "a.wav")})
    assert exc_info.value.code == VOXCPM_INVALID_PARAMS


def test_synthesis_rejects_missing_reference_file(tmp_path: Path):
    backend, _ = _backend_with_model()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_clone(
            {
                "text": "hi",
                "output_path": str(tmp_path / "a.wav"),
                "reference_wav_path": str(tmp_path / "missing.wav"),
            }
        )
    assert exc_info.value.code == VOXCPM_REFERENCE_INVALID


def test_synthesis_passes_generate_kwargs_and_writes_48k_wav(tmp_path: Path):
    backend, fake = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF....")
    output = tmp_path / "out.wav"

    result = backend.synthesize_clone(
        {
            "text": "Xin chào VoxCPM2",
            "output_path": str(output),
            "reference_wav_path": str(reference),
            "cfg_value": 2.5,
            "inference_timesteps": 12,
            "seed": 42,
        }
    )

    assert Path(result["output_path"]) == output
    assert result["sample_rate"] == 48000
    assert result["backend"] == "real"
    assert result["method"] == "synthesize_clone"
    assert output.is_file()
    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getframerate() == 48000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getnframes() == 48000  # 1.0 s of fake audio

    call = fake.generate_calls[0]
    assert call["text"] == "Xin chào VoxCPM2"
    assert call["reference_wav_path"] == str(reference)
    assert call["cfg_value"] == 2.5
    assert call["inference_timesteps"] == 12
    assert call["seed"] == 42


def test_synthesis_uses_defaults_and_creates_output_dirs(tmp_path: Path):
    backend, fake = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")
    nested_output = tmp_path / "deep" / "dir" / "out.wav"

    result = backend.synthesize_clone(
        {"text": "hi", "output_path": str(nested_output), "reference_wav_path": str(reference)}
    )
    assert nested_output.is_file()
    call = fake.generate_calls[0]
    assert call["cfg_value"] == 2.0  # DEFAULT_CFG_VALUE
    assert call["inference_timesteps"] == 10  # DEFAULT_INFERENCE_TIMESTEPS
    assert "seed" not in call
    assert result["duration_seconds"] > 0


def test_ultimate_not_implemented_until_phase8(tmp_path: Path):
    """Ultimate clone stays deferred (plan: LATER). Emotional is Phase 5."""
    backend, _ = _backend_with_model()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_ultimate({"text": "hi", "output_path": str(tmp_path / "x.wav")})
    assert exc_info.value.code == VOXCPM_NOT_IMPLEMENTED


def test_warmup_requires_model():
    backend = RealVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.warmup()
    assert exc_info.value.code == VOXCPM_MODEL_NOT_LOADED


def test_warmup_with_model_uses_neutral_defaults():
    backend, fake = _backend_with_model()
    result = backend.warmup()
    assert result["status"] == "warmed"
    call = fake.generate_calls[0]
    assert call["text"] == "Xin chào."
    assert call["cfg_value"] == 2.0
    assert call["inference_timesteps"] == 10
    assert "reference_wav_path" not in call  # neutral warmup


def test_analyze_reference_basic_shape(tmp_path: Path):
    backend = RealVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.analyze_reference({"audio_path": str(tmp_path / "nope.wav")})
    assert exc_info.value.code == VOXCPM_REFERENCE_INVALID

    # A real WAV file reports duration from the header
    wav_path = tmp_path / "ref.wav"
    _write_wav_48k(wav_path, np.zeros(96000, dtype=np.float32), 48000)
    result = backend.analyze_reference({"audio_path": str(wav_path)})
    assert result["backend"] == "real"
    assert abs(result["duration_seconds"] - 2.0) < 1e-6


def test_write_wav_48k_roundtrip(tmp_path: Path):
    output = tmp_path / "wav.wav"
    _write_wav_48k(output, np.full(48000, 0.25, dtype=np.float32), 48000)
    with wave.open(str(output), "rb") as source:
        assert source.getframerate() == 48000
        assert source.getnchannels() == 1
        assert source.getsampwidth() == 2
        assert abs(source.getnframes() / 48000 - 1.0) < 1e-6


def test_inference_failure_wrapped_as_voxcpm_inference_failed(tmp_path: Path):
    class BrokenModel:
        tts_model = FakeTTSModel()
        device = "cpu"

        def generate(self, **kwargs):
            raise RuntimeError("CUDA OOM")

    backend = RealVoxCpmBackend()
    backend.model = BrokenModel()
    backend.sample_rate = 48000
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_clone(
            {
                "text": "hi",
                "output_path": str(tmp_path / "o.wav"),
                "reference_wav_path": str(reference),
            }
        )
    assert exc_info.value.code == "VOXCPM_INFERENCE_FAILED"
    assert "CUDA OOM" in exc_info.value.message

# ---- Phase 5: emotional synthesis ----


def test_emotional_requires_model(tmp_path: Path):
    backend = RealVoxCpmBackend()
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_emotional({"text": "hi", "output_path": str(tmp_path / "e.wav")})
    assert exc_info.value.code == VOXCPM_MODEL_NOT_LOADED


def test_emotional_preset_compiles_to_instruction(tmp_path: Path):
    backend, fake = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")
    output = tmp_path / "e.wav"

    result = backend.synthesize_emotional(
        {
            "text": "Anh vẫn nhớ ngày hôm đó.",
            "output_path": str(output),
            "reference_wav_path": str(reference),
            "emotion": "sad",
        }
    )

    assert result["method"] == "synthesize_emotional"
    assert "trying not to cry" in result["instruction"]
    # Controlled text = "(instruction)text" per plan.
    call = fake.generate_calls[0]
    assert call["text"].startswith("(Sad, restrained")
    assert call["text"].endswith("Anh vẫn nhớ ngày hôm đó.")
    # Identity still comes from the reference audio.
    assert call["reference_wav_path"] == str(reference)


def test_emotional_custom_instruction_used_verbatim(tmp_path: Path):
    backend, fake = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")

    result = backend.synthesize_emotional(
        {
            "text": "hello",
            "output_path": str(tmp_path / "e2.wav"),
            "reference_wav_path": str(reference),
            "instruction": "very slow, dreamy narration",
        }
    )
    assert result["instruction"] == "very slow, dreamy narration"
    assert fake.generate_calls[0]["text"] == "(very slow, dreamy narration)hello"


def test_emotional_neutral_preset_no_wrapper(tmp_path: Path):
    backend, fake = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")

    backend.synthesize_emotional(
        {
            "text": "plain",
            "output_path": str(tmp_path / "e3.wav"),
            "reference_wav_path": str(reference),
            "emotion": "neutral",
        }
    )
    assert fake.generate_calls[0]["text"] == "plain"


def test_emotional_unknown_preset_fails_fast(tmp_path: Path):
    backend, _ = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")
    with pytest.raises(WorkerError) as exc_info:
        backend.synthesize_emotional(
            {
                "text": "hi",
                "output_path": str(tmp_path / "e4.wav"),
                "reference_wav_path": str(reference),
                "emotion": "super_duper",
            }
        )
    assert exc_info.value.code == VOXCPM_INVALID_PARAMS


def test_emotional_output_still_48k_wav(tmp_path: Path):
    backend, _ = _backend_with_model()
    reference = tmp_path / "ref.wav"
    reference.write_bytes(b"RIFF")
    output = tmp_path / "e5.wav"
    backend.synthesize_emotional(
        {
            "text": "hi",
            "output_path": str(output),
            "reference_wav_path": str(reference),
            "emotion": "cheerful",
        }
    )
    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getframerate() == 48000
        assert wav_file.getnchannels() == 1


def test_all_ten_emotion_presets_compile(tmp_path: Path):
    """Each preset maps to a distinct non-empty (except neutral) instruction."""
    from real_backend import EMOTION_PRESET_INSTRUCTIONS

    assert len(EMOTION_PRESET_INSTRUCTIONS) == 10
    instructions = [v for k, v in EMOTION_PRESET_INSTRUCTIONS.items() if k != "neutral"]
    assert len(set(instructions)) == len(instructions)  # all distinct
    assert EMOTION_PRESET_INSTRUCTIONS["neutral"] == ""
