"""Real VoxCPM2 backend.

Implemented in Phase 4: neutral cloning only. The voxcpm import is deferred
until load_model so the module is safe to import (and test) without the
package installed. Never falls back to the mock backend.

Requires the voxcpm package in a dedicated worker environment
(Python >=3.10,<3.13 + torch >=2.5) — never the FastAPI main environment.
"""

from __future__ import annotations

import json
import logging
import os
import struct
import wave
from pathlib import Path
from typing import Any

import numpy as np

from backend import VoxCpmBackend
from errors import (
    VOXCPM_INFERENCE_FAILED,
    VOXCPM_INVALID_PARAMS,
    VOXCPM_MODEL_NOT_LOADED,
    VOXCPM_PACKAGE_NOT_INSTALLED,
    VOXCPM_REFERENCE_INVALID,
    WorkerError,
)
from path_utils import validate_path

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "openbmb/VoxCPM2"
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_CFG_VALUE = 2.0
DEFAULT_INFERENCE_TIMESTEPS = 10

# Phase 5: emotion presets compiled to natural-language instructions.
# Plan rule: presets are NOT engine enums — each maps to a performance
# instruction; identity comes from the reference audio, instruction is the
# performance.
EMOTION_PRESET_INSTRUCTIONS: dict[str, str] = {
    "neutral": "",
    "cheerful": "Cheerful, bright and upbeat, lively pacing, warm smiling tone",
    "excited": "Excited and energetic, fast enthusiastic pacing, elevated volume",
    "sad": "Sad, restrained, speaking slowly, soft volume, trying not to cry",
    "angry": "Angry, tense and sharp, clipped aggressive delivery",
    "fearful": "Fearful and anxious, trembling hesitant voice, uneven pacing",
    "gentle": "Gentle and tender, soft volume, slow soothing pacing",
    "whisper": "Whispered, very soft breathy voice, close intimate delivery",
    "calm": "Calm and steady, even relaxed pacing, neutral soft volume",
    "storytelling": "Warm storytelling narration, expressive measured pacing, drawing the listener in",
}


def _import_error() -> Exception | None:
    try:
        import voxcpm  # noqa: F401

        return None
    except Exception as exc:  # pragma: no cover - exercised only without the package
        return exc


class RealVoxCpmBackend(VoxCpmBackend):
    """Backend delegating to the installed voxcpm package (neutral clone only)."""

    def __init__(self) -> None:
        self.model: Any | None = None
        self.device: str = "cpu"
        self.model_id: str = DEFAULT_MODEL_ID
        self.sample_rate: int = DEFAULT_SAMPLE_RATE
        self._loader_used: str = "stock"
        self._import_error: Exception | None = _import_error()

    # ---- contract methods ----

    def ping(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"pong": True, "mock": False, "mode": "real"}

    def runtime_info(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ready": self.model is not None,
            "model_loaded": self.model is not None,
            "device": self.device,
            "backend": "real",
            "sample_rate": self.sample_rate,
            "model_id": self.model_id,
            "package_installed": self._import_error is None,
        }

    def load_model(self, params: dict[str, Any]) -> dict[str, Any]:
        if self._import_error is not None:
            raise WorkerError(
                VOXCPM_PACKAGE_NOT_INSTALLED,
                f"Failed to import voxcpm: {self._import_error}",
            )

        model_id = params.get("model_id", DEFAULT_MODEL_ID)
        device = params.get("device", "auto")

        # Memory-frugal load first. The stock VoxCPM.from_pretrained builds
        # the model in fp32 (~9GB) before casting to bf16 and materializes
        # the full 4.3GB state dict — on RAM-constrained hosts (16GB) that
        # exceeds the commit limit and crashes with a native segfault inside
        # model construction. The bf16-direct path below peaks at roughly
        # half that and loads the same config + checkpoint.
        try:
            self.model = self._load_memory_frugal(model_id, device)
            self._loader_used = "memory_frugal"
        except Exception as frugal_exc:
            logger.warning(
                "Memory-frugal VoxCPM2 load failed (%s); falling back to stock loader",
                frugal_exc,
            )
            # Deferred heavy import — happens only on first load.
            from voxcpm import VoxCPM  # type: ignore[import-not-found]

            load_kwargs: dict[str, Any] = {"load_denoiser": False}
            if device and device != "auto":
                load_kwargs["device"] = device
            try:
                self.model = VoxCPM.from_pretrained(model_id, **load_kwargs)
            except TypeError:
                # Older builds may not accept load_denoiser.
                self.model = VoxCPM.from_pretrained(model_id)
            self._loader_used = "stock"

        self.model_id = model_id
        self.device = self._resolve_device()
        self.sample_rate = int(
            getattr(getattr(self.model, "tts_model", None), "sample_rate", DEFAULT_SAMPLE_RATE)
        )
        return {
            "status": "loaded",
            "backend": "real",
            "device": self.device,
            "sample_rate": self.sample_rate,
            "loader": self._loader_used,
        }

    def _load_memory_frugal(self, model_id: str, device: str) -> Any:
        """Load VoxCPM2 in bf16 with a streaming (non-mmap) checkpoint read.

        Replicates VoxCPM.from_pretrained -> VoxCPM2Model.from_local but
        (1) constructs the model under torch.set_default_dtype(bfloat16) so
        no fp32 copy of the weights ever exists, and (2) reads checkpoint
        tensors one-by-one with plain file I/O instead of safe_open, whose
        whole-file CreateFileMapping can be refused by the Windows commit
        limit when the machine is already under memory pressure
        ("os error 1455"). Any deviation (missing files, non-voxcpm2
        architecture, uncached snapshot) raises and the caller falls back to
        the stock loader.
        """
        import json as _json

        if os.path.isdir(model_id):
            local_path = model_id
        else:
            try:
                from huggingface_hub import snapshot_download

                local_path = str(snapshot_download(repo_id=model_id, local_files_only=True))
            except Exception as exc:
                raise RuntimeError(f"Snapshot not cached for {model_id}: {exc}") from exc

        import torch  # type: ignore[import-not-found]

        config_path = os.path.join(local_path, "config.json")
        with open(config_path, "r", encoding="utf-8") as cfg_f:
            raw_config = _json.load(cfg_f)
        if raw_config.get("architecture", "").lower() != "voxcpm2":
            raise RuntimeError(f"Not a voxcpm2 checkpoint: {config_path}")
        if not os.path.isfile(os.path.join(local_path, "model.safetensors")):
            raise RuntimeError("model.safetensors not found in snapshot")

        # Set default dtype BEFORE any module construction so the model is
        # born bf16 and never exists as a fp32 copy.
        torch.set_default_dtype(torch.bfloat16)
        try:
            from voxcpm.model.voxcpm2 import VoxCPM2Model, VoxCPMConfig
            from transformers import LlamaTokenizerFast
            from voxcpm.modules.audiovae import AudioVAEV2

            with open(config_path, "r", encoding="utf-8") as cfg_f:
                config = VoxCPMConfig.model_validate_json(cfg_f.read())
            tokenizer = LlamaTokenizerFast.from_pretrained(local_path)
            audio_vae = AudioVAEV2(config=config.audio_vae_config)
            tts_model = VoxCPM2Model(
                config,
                tokenizer,
                audio_vae,
                None,
                device=None if device == "auto" else device,
            )
            tts_model.audio_vae = tts_model.audio_vae.to(torch.float32)

            model_state = tts_model.state_dict()
            copied = _stream_safetensors_into(
                os.path.join(local_path, "model.safetensors"), model_state
            )
            # The safetensors file holds the LM/DiT/projection weights; the
            # fp32 audio_vae.* keys load separately from audiovae.pth, so
            # coverage is judged against the non-VAE keys only.
            non_vae_total = sum(1 for key in model_state if not key.startswith("audio_vae."))
            if copied < non_vae_total * 0.95:
                raise RuntimeError(
                    f"Checkpoint coverage too low: {copied}/{non_vae_total} non-VAE keys"
                )

            vae_sd = torch.load(
                os.path.join(local_path, "audiovae.pth"),
                map_location="cpu",
                weights_only=True,
            )
            vae_sd = vae_sd.get("state_dict", vae_sd)
            for key, value in vae_sd.items():
                full_key = f"audio_vae.{key}"
                if full_key in model_state:
                    model_state[full_key].copy_(value.to(model_state[full_key].dtype))

            tts_model = tts_model.to(tts_model.device).eval().optimize(disable=True)
            tts_model.audio_vae = tts_model.audio_vae.to(torch.float32)
        finally:
            torch.set_default_dtype(torch.float32)

        wrapper = _VoxCpmWrapper(tts_model)
        return wrapper
        """Load VoxCPM2 in bf16 with a streaming state-dict copy.

        Replicates VoxCPM.from_pretrained -> VoxCPM2Model.from_local but
        (1) constructs the model under torch.set_default_dtype(bfloat16) so
        no fp32 copy of the weights ever exists, and (2) copies checkpoint
        tensors one-by-one via safe_open.get_tensor instead of materializing
        the whole 4.3GB safetensors dict. Any deviation (missing files,
        non-voxcpm2 architecture, uncached snapshot) raises and the caller
        falls back to the stock loader.
        """
        import json as _json

        if os.path.isdir(model_id):
            local_path = model_id
        else:
            try:
                from huggingface_hub import snapshot_download

                local_path = str(snapshot_download(repo_id=model_id, local_files_only=True))
            except Exception as exc:
                raise RuntimeError(f"Snapshot not cached for {model_id}: {exc}") from exc

        import torch  # type: ignore[import-not-found]

        config_path = os.path.join(local_path, "config.json")
        with open(config_path, "r", encoding="utf-8") as cfg_f:
            raw_config = _json.load(cfg_f)
        if raw_config.get("architecture", "").lower() != "voxcpm2":
            raise RuntimeError(f"Not a voxcpm2 checkpoint: {config_path}")
        if not os.path.isfile(os.path.join(local_path, "model.safetensors")):
            raise RuntimeError("model.safetensors not found in snapshot")

        # Map the checkpoint BEFORE constructing the model: once the bf16
        # model + KV cache are resident (~8GB), CreateFileMapping of the
        # 4.3GB file can be refused by the Windows commit limit
        # ("os error 1455"). While the process is still small the mapping
        # always succeeds; the handle is then used to stream tensors in.
        from safetensors import safe_open

        ckpt_handle = safe_open(
            os.path.join(local_path, "model.safetensors"), framework="pt", device="cpu"
        )

        # Set default dtype BEFORE any module construction so the model is
        # born bf16 and never exists as a fp32 copy.
        torch.set_default_dtype(torch.bfloat16)
        try:
            from voxcpm.model.voxcpm2 import VoxCPM2Model, VoxCPMConfig
            from transformers import LlamaTokenizerFast
            from voxcpm.modules.audiovae import AudioVAEV2

            with open(config_path, "r", encoding="utf-8") as cfg_f:
                config = VoxCPMConfig.model_validate_json(cfg_f.read())
            tokenizer = LlamaTokenizerFast.from_pretrained(local_path)
            audio_vae = AudioVAEV2(config=config.audio_vae_config)
            tts_model = VoxCPM2Model(
                config,
                tokenizer,
                audio_vae,
                None,
                device=None if device == "auto" else device,
            )
            tts_model.audio_vae = tts_model.audio_vae.to(torch.float32)

            model_state = tts_model.state_dict()
            copied = 0
            for key in ckpt_handle.keys():
                if key not in model_state:
                    continue
                model_state[key].copy_(
                    ckpt_handle.get_tensor(key).to(model_state[key].dtype)
                )
                copied += 1

            if copied < len(model_state) * 0.9:
                raise RuntimeError(
                    f"Checkpoint coverage too low: {copied}/{len(model_state)} keys"
                )

            vae_sd = torch.load(
                os.path.join(local_path, "audiovae.pth"),
                map_location="cpu",
                weights_only=True,
            )
            vae_sd = vae_sd.get("state_dict", vae_sd)
            for key, value in vae_sd.items():
                full_key = f"audio_vae.{key}"
                if full_key in model_state:
                    model_state[full_key].copy_(value.to(model_state[full_key].dtype))

            tts_model = tts_model.to(tts_model.device).eval().optimize(disable=True)
            tts_model.audio_vae = tts_model.audio_vae.to(torch.float32)
        finally:
            ckpt_handle.__exit__(None, None, None)
            torch.set_default_dtype(torch.float32)

        wrapper = _VoxCpmWrapper(tts_model)
        return wrapper

    def unload_model(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        released = self.model is not None
        self.model = None
        self.device = "cpu"
        return {"status": "unloaded", "backend": "real", "released": released}

    def warmup(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.model is None:
            raise WorkerError(VOXCPM_MODEL_NOT_LOADED, "Model is not loaded.")
        params = params or {}
        reference_wav_path = params.get("reference_wav_path")
        generate_kwargs: dict[str, Any] = {
            "text": "Xin chào.",
            "cfg_value": DEFAULT_CFG_VALUE,
            "inference_timesteps": DEFAULT_INFERENCE_TIMESTEPS,
        }
        if reference_wav_path:
            generate_kwargs["reference_wav_path"] = str(validate_path(reference_wav_path))
        self._generate(generate_kwargs)
        return {"status": "warmed", "backend": "real"}

    def analyze_reference(self, params: dict[str, Any]) -> dict[str, Any]:
        audio_path = validate_path(params["audio_path"])
        if not audio_path.is_file():
            raise WorkerError(VOXCPM_REFERENCE_INVALID, "Reference audio not found.")
        duration = params.get("duration")
        if duration is None:
            duration = _wav_duration_seconds(audio_path)
        # Neutral clone does not need embedding analysis; report basic truth.
        return {
            "audio_path": str(audio_path),
            "duration_seconds": float(duration or 0.0),
            "sample_rate": self.sample_rate,
            "backend": "real",
        }

    def synthesize_clone(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._synthesize(params, use_reference=True)

    def synthesize_emotional(self, params: dict[str, Any]) -> dict[str, Any]:
        """Phase 5: emotional TTS from a cloned voice.

        reference audio = voice identity; instruction = performance.
        The preset is compiled to a natural-language instruction and wrapped
        around the text: controlled_text = f"({instruction}){text}".
        """
        self._require_model()

        text = params.get("text")
        if not text or not isinstance(text, str):
            raise WorkerError(VOXCPM_INVALID_PARAMS, "Synthesis requires non-empty 'text'.")

        instruction = self._resolve_instruction(params)
        controlled_text = f"({instruction}){text}" if instruction else text

        emotional_params = dict(params)
        emotional_params["text"] = controlled_text
        result = self._synthesize(emotional_params, use_reference=True)
        result["method"] = "synthesize_emotional"
        result["instruction"] = instruction or None
        return result

    def synthesize_ultimate(self, params: dict[str, Any]) -> dict[str, Any]:
        raise WorkerError(
            "VOXCPM_NOT_IMPLEMENTED",
            "Ultimate clone is deferred to Phase 8 (plan: LATER).",
        )

    # ---- internals ----

    def _resolve_instruction(self, params: dict[str, Any]) -> str:
        """Compile an emotion preset / custom instruction to performance text.

        Priority: explicit instruction > emotion preset > neutral (empty).
        """
        instruction = params.get("instruction")
        if isinstance(instruction, str) and instruction.strip():
            return instruction.strip()
        emotion = params.get("emotion")
        if isinstance(emotion, str) and emotion.strip():
            key = emotion.strip().lower()
            if key in EMOTION_PRESET_INSTRUCTIONS:
                return EMOTION_PRESET_INSTRUCTIONS[key]
            raise WorkerError(
                VOXCPM_INVALID_PARAMS,
                f"Unknown emotion preset '{emotion}'. Valid: "
                + ", ".join(sorted(EMOTION_PRESET_INSTRUCTIONS)),
            )
        return ""

    def _resolve_device(self) -> str:
        if self.model is None:
            return "cpu"
        # VoxCPM stores device info loosely; try common attributes.
        for attr in ("device", "_device"):
            device = getattr(self.model, attr, None)
            if device:
                return str(device)
        try:
            import torch  # type: ignore[import-not-found]

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _require_model(self) -> Any:
        if self.model is None:
            raise WorkerError(VOXCPM_MODEL_NOT_LOADED, "Model is not loaded.")
        return self.model

    def _synthesize(self, params: dict[str, Any], *, use_reference: bool = True) -> dict[str, Any]:
        model = self._require_model()

        text = params.get("text")
        if not text or not isinstance(text, str):
            raise WorkerError(VOXCPM_INVALID_PARAMS, "Synthesis requires non-empty 'text'.")

        output_path = validate_path(params["output_path"])
        reference_wav_path = params.get("reference_wav_path")
        if use_reference:
            if not reference_wav_path:
                raise WorkerError(
                    VOXCPM_INVALID_PARAMS,
                    "synthesize_clone requires 'reference_wav_path'.",
                )
            reference_path = Path(reference_wav_path)
            if not reference_path.is_file():
                raise WorkerError(
                    VOXCPM_REFERENCE_INVALID,
                    "Reference audio not found.",
                )
            reference_wav_path = str(validate_path(reference_wav_path))

        generate_kwargs: dict[str, Any] = {
            "text": text,
            "cfg_value": float(params.get("cfg_value", DEFAULT_CFG_VALUE)),
            "inference_timesteps": int(params.get("inference_timesteps", DEFAULT_INFERENCE_TIMESTEPS)),
        }
        seed = params.get("seed")
        if seed is not None:
            generate_kwargs["seed"] = int(seed)
        if use_reference and reference_wav_path:
            generate_kwargs["reference_wav_path"] = reference_wav_path

        wav = self._generate(generate_kwargs)
        if wav is None:
            raise WorkerError(VOXCPM_INFERENCE_FAILED, "Model returned empty audio.")
        # Model output is [1, N] (or [N]); flatten before length math so
        # duration_seconds reflects the written audio, not the batch dim.
        flat_wav = np.asarray(wav).reshape(-1)
        if flat_wav.size == 0:
            raise WorkerError(VOXCPM_INFERENCE_FAILED, "Model returned empty audio.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_wav_48k(output_path, flat_wav, self.sample_rate)
        duration_seconds = flat_wav.size / self.sample_rate
        return {
            "output_path": str(output_path),
            "sample_rate": self.sample_rate,
            "duration_seconds": duration_seconds,
            "backend": "real",
            "method": "synthesize_clone",
        }

    def _generate(self, generate_kwargs: dict[str, Any]) -> Any:
        try:
            return self.model.generate(**generate_kwargs)
        except Exception as exc:
            raise WorkerError(
                VOXCPM_INFERENCE_FAILED,
                f"VoxCPM2 inference failed: {type(exc).__name__}: {exc}",
            ) from exc


_SAFETENSORS_DTYPES: dict[str, Any] = {
    "F64": "float64",
    "F32": "float32",
    "F16": "float16",
    "BF16": "bfloat16",
    "I64": "int64",
    "I32": "int32",
    "I16": "int16",
    "I8": "int8",
    "U8": "uint8",
    "BOOL": "bool",
}


def _stream_safetensors_into(file_path: str, model_state: dict) -> int:
    """Copy safetensors checkpoint tensors into model_state without mmap.

    Reads the JSON header, then per-tensor seeks + reads with plain file
    I/O and copy_()s into the existing parameter storage. Avoids
    safe_open's whole-file CreateFileMapping, which the Windows commit
    limit can refuse under memory pressure (os error 1455). Returns the
    number of tensors copied.
    """
    import torch  # type: ignore[import-not-found]

    copied = 0
    with open(file_path, "rb") as source:
        header_len = int.from_bytes(source.read(8), "little")
        header = json.loads(source.read(header_len))
        data_start = 8 + header_len
        for key, meta in header.items():
            if key == "__metadata__" or key not in model_state:
                continue
            start, end = meta["data_offsets"]
            source.seek(data_start + start)
            buf = source.read(end - start)
            tensor = torch.frombuffer(
                bytearray(buf), dtype=getattr(torch, _SAFETENSORS_DTYPES[meta["dtype"]])
            ).view(meta["shape"])
            model_state[key].copy_(tensor.to(model_state[key].dtype))
            copied += 1
    return copied


class _VoxCpmWrapper:
    """Minimal stand-in for the voxcpm.VoxCPM pipeline wrapper.

    The memory-frugal loader builds the VoxCPM2Model directly; the rest of
    the backend (generate delegation, sample_rate lookup via
    ``model.tts_model``) only needs this attribute shape. generate() adapts
    the pipeline-level kwargs (text, seed) to the model-level signature
    (target_text, no seed param — seeding is done via torch.manual_seed).
    """

    def __init__(self, tts_model: Any) -> None:
        self.tts_model = tts_model

    def generate(self, *args: Any, **kwargs: Any) -> Any:
        adapted = dict(kwargs)
        text = adapted.pop("text", None)
        if text is not None and "target_text" not in adapted:
            adapted["target_text"] = text
        seed = adapted.pop("seed", None)
        if seed is not None:
            import torch  # type: ignore[import-not-found]

            torch.manual_seed(int(seed))
        return self.tts_model.generate(*args, **adapted)


def _wav_duration_seconds(path: Path) -> float | None:
    try:
        import wave

        with wave.open(str(path), "rb") as source:
            sample_rate = source.getframerate()
            return source.getnframes() / sample_rate if sample_rate > 0 else None
    except Exception:
        return None


def _write_wav_48k(path: Path, audio: "np.ndarray", sample_rate: int) -> None:
    """Write a mono f32 numpy array to a 16-bit PCM WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype("<i2")
    byte_count = int(pcm.nbytes)
    header = b"RIFF"
    header += struct.pack("<I", 36 + byte_count)
    header += b"WAVE"
    header += b"fmt "
    header += struct.pack("<I", 16)
    header += struct.pack("<H", 1)  # PCM
    header += struct.pack("<H", 1)  # mono
    header += struct.pack("<I", sample_rate)
    header += struct.pack("<I", sample_rate * 2)
    header += struct.pack("<H", 2)
    header += struct.pack("<H", 16)
    header += b"data"
    header += struct.pack("<I", byte_count)
    path.write_bytes(header + pcm.tobytes())