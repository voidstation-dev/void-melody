"""Voice Lab Enrollment v2 artifact management (NPZ serialization with allow_pickle=False)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EnrollmentArtifactError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def compute_reference_fingerprint(target: Path | bytes) -> str:
    """Compute SHA-256 fingerprint for audio data or file."""
    hasher = hashlib.sha256()
    if isinstance(target, bytes):
        hasher.update(target)
    else:
        with open(target, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
    return hasher.hexdigest()


def save_enrollment_artifact(
    target_dir: Path,
    *,
    speaker_emb: np.ndarray,
    ref_codes: np.ndarray | None,
    metadata: dict[str, Any],
) -> Path:
    """Atomically save speaker embedding and reference codes into enrollment-v2.npz and enrollment.json."""
    target_dir.mkdir(parents=True, exist_ok=True)
    npz_path = target_dir / "enrollment-v2.npz"
    tmp_npz_path = target_dir / "enrollment-v2.tmp.npz"
    json_path = target_dir / "enrollment.json"

    emb = np.asarray(speaker_emb, dtype=np.float32)
    if not np.all(np.isfinite(emb)):
        raise EnrollmentArtifactError(
            "INVALID_EMBEDDING", "Speaker embedding contains non-finite numbers (NaN/Inf)."
        )

    arrays_to_save: dict[str, np.ndarray] = {"speaker_emb": emb}
    if ref_codes is not None:
        codes = np.asarray(ref_codes, dtype=np.int64)
        arrays_to_save["ref_codes"] = codes

    try:
        np.savez_compressed(tmp_npz_path, **arrays_to_save)
        # Validation round-trip before atomic move
        with np.load(tmp_npz_path, allow_pickle=False) as loaded:
            if "speaker_emb" not in loaded:
                raise EnrollmentArtifactError(
                    "CORRUPT_ARTIFACT", "Validation failed: speaker_emb missing in saved artifact."
                )
            if not np.all(np.isfinite(loaded["speaker_emb"])):
                raise EnrollmentArtifactError(
                    "CORRUPT_ARTIFACT", "Validation failed: speaker_emb contains NaN/Inf values."
                )

        tmp_npz_path.replace(npz_path)

        meta_clean = {
            "formatVersion": metadata.get("formatVersion", "vieneu-enrollment-v2"),
            "providerId": metadata.get("providerId", "vieneu"),
            "engineId": metadata.get("engineId", "v3turbo"),
            "engineVersion": metadata.get("engineVersion"),
            "referenceFingerprint": metadata.get("referenceFingerprint"),
            "referenceSampleRate": metadata.get("referenceSampleRate", 44100),
            "referenceDuration": metadata.get("referenceDuration"),
            "denoiseMode": metadata.get("denoiseMode", "auto"),
            "denoiseApplied": metadata.get("denoiseApplied", False),
            "defaultCloneMode": metadata.get("defaultCloneMode", "fidelity"),
            "speakerSimilarityScore": metadata.get("speakerSimilarityScore"),
            "calibrationQualityScore": metadata.get("calibrationQualityScore"),
        }
        json_path.write_text(json.dumps(meta_clean, indent=2, ensure_ascii=False), encoding="utf-8")
        return npz_path
    except Exception as exc:
        tmp_npz_path.unlink(missing_ok=True)
        if isinstance(exc, EnrollmentArtifactError):
            raise
        raise EnrollmentArtifactError("SAVE_FAILED", f"Failed saving enrollment artifact: {exc}") from exc


def load_enrollment_artifact(
    artifact_path: Path,
) -> tuple[np.ndarray, np.ndarray | None, dict[str, Any]]:
    """Load enrollment artifact securely with allow_pickle=False."""
    if not artifact_path.is_file():
        raise EnrollmentArtifactError("ARTIFACT_NOT_FOUND", f"Artifact not found: {artifact_path}")

    try:
        with np.load(artifact_path, allow_pickle=False) as loaded:
            if "speaker_emb" not in loaded:
                raise EnrollmentArtifactError(
                    "INVALID_ARTIFACT", "speaker_emb key missing in NPZ artifact."
                )
            speaker_emb = np.array(loaded["speaker_emb"], dtype=np.float32)
            if not np.all(np.isfinite(speaker_emb)):
                raise EnrollmentArtifactError(
                    "CORRUPT_ARTIFACT", "speaker_emb contains non-finite numbers."
                )

            ref_codes = (
                np.array(loaded["ref_codes"], dtype=np.int64) if "ref_codes" in loaded else None
            )

        json_path = artifact_path.parent / "enrollment.json"
        metadata: dict[str, Any] = {}
        if json_path.is_file():
            try:
                metadata = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                logger.warning("Could not parse enrollment.json at %s", json_path)

        return speaker_emb, ref_codes, metadata
    except Exception as exc:
        if isinstance(exc, EnrollmentArtifactError):
            raise
        raise EnrollmentArtifactError(
            "LOAD_FAILED", f"Could not load artifact {artifact_path}: {exc}"
        ) from exc
