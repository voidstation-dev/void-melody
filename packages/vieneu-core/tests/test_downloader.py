"""Tests for the model downloader, manifest, and checksum verification.

No real network calls. ``hf_hub_download`` is monkeypatched to simulate
downloads. The tests verify the manifest shape, checksum verification, the
download semaphore (concurrency=1), and error mapping.
"""

import dataclasses
import hashlib
import sys

import pytest

from vieneu_core.downloader import (
    ModelDownloader,
    ModelFile,
    ModelManifest,
    default_manifests,
    ensure_default_model_artifacts,
    verify_cache,
    verify_file,
)
from vieneu_core.errors import ModelLoadFailedError


def test_default_manifests_pin_revisions():
    manifests = default_manifests()
    assert len(manifests) == 2
    repos = {m.repo_id for m in manifests}
    assert "pnnbao-ump/VieNeu-TTS-v3-Turbo" in repos
    assert "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX" in repos
    # Revisions must be SHAs, not branch names like "main".
    for m in manifests:
        assert len(m.revision) >= 20  # SHA-like
        assert m.revision != "main"


def test_default_manifests_include_voice_clone_artifacts():
    manifests = default_manifests()
    vieneu = next(m for m in manifests if m.repo_id == "pnnbao-ump/VieNeu-TTS-v3-Turbo")
    codec = next(
        m
        for m in manifests
        if m.repo_id == "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX"
    )

    vieneu_files = {entry.filename for entry in vieneu.files}
    assert {
        "speaker_encoder.onnx",
        "denoiser.onnx",
        "onnx_int8/vieneu_prefill.onnx",
        "onnx_int8/vieneu_decode_step.onnx",
        "onnx_int8/vieneu_acoustic_cached.onnx",
        "onnx_int8/vieneu_backbone_shared.data",
        "onnx_int8/vieneu_v3_heads.npz",
        "onnx_int8/config.json",
        "onnx_int8/tokenizer.json",
    }.issubset(vieneu_files)

    codec_files = {entry.filename for entry in codec.files}
    assert {
        "moss_audio_tokenizer_encode.onnx",
        "moss_audio_tokenizer_encode.data",
        "moss_audio_tokenizer_decode_full.onnx",
        "moss_audio_tokenizer_decode_shared.data",
        "moss_audio_tokenizer_decode_step.onnx",
        "codec_browser_onnx_meta.json",
    }.issubset(codec_files)


def test_manifest_is_frozen():
    m = ModelManifest(repo_id="x", revision="sha", files=(ModelFile(filename="a"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.repo_id = "other"  # type: ignore[misc]


def test_verify_file_missing(tmp_path):
    assert verify_file(tmp_path / "missing", expected_sha256=None) is False


def test_verify_file_no_checksum(tmp_path):
    f = tmp_path / "f"
    f.write_bytes(b"hello")
    assert verify_file(f, expected_sha256=None) is True


def test_verify_file_good_checksum(tmp_path):
    f = tmp_path / "f"
    data = b"hello world"
    f.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    assert verify_file(f, expected_sha256=digest) is True


def test_verify_file_bad_checksum(tmp_path):
    f = tmp_path / "f"
    f.write_bytes(b"tampered")
    assert verify_file(f, expected_sha256="0" * 64) is False


def test_verify_cache_all_present(tmp_path):
    f = tmp_path / "a"
    f.write_bytes(b"x")
    manifest = ModelManifest(
        repo_id="x",
        revision="sha",
        files=(
            ModelFile(filename="a", expected_sha256=hashlib.sha256(b"x").hexdigest()),
        ),
    )
    assert verify_cache(manifest, tmp_path) is True


def test_verify_cache_missing_file(tmp_path):
    manifest = ModelManifest(
        repo_id="x",
        revision="sha",
        files=(ModelFile(filename="missing"),),
    )
    assert verify_cache(manifest, tmp_path) is False


@pytest.mark.asyncio
async def test_downloader_calls_hub_with_pinned_revision(tmp_path, monkeypatch):
    calls = []

    def fake_download(repo_id, filename, revision, cache_dir=None, **kwargs):
        calls.append((repo_id, filename, revision))
        out = tmp_path / filename
        out.write_bytes(b"data")
        return str(out)

    # Patch the lazy import inside _download_one.

    fake_hub = type("M", (), {"hf_hub_download": staticmethod(fake_download)})
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)

    manifest = ModelManifest(
        repo_id="org/repo",
        revision="abc123sha",
        files=(ModelFile(filename="model.onnx"),),
    )
    downloader = ModelDownloader(cache_dir=tmp_path)
    paths = await downloader.download_manifest(manifest)
    assert len(paths) == 1
    assert calls[0][0] == "org/repo"
    assert calls[0][2] == "abc123sha"  # pinned revision used


@pytest.mark.asyncio
async def test_downloader_raises_on_network_error(tmp_path, monkeypatch):
    def fake_download(*args, **kwargs):
        raise ConnectionError("network down")

    fake_hub = type("M", (), {"hf_hub_download": staticmethod(fake_download)})
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)

    manifest = ModelManifest(
        repo_id="org/repo",
        revision="sha",
        files=(ModelFile(filename="f"),),
    )
    downloader = ModelDownloader(cache_dir=tmp_path)
    with pytest.raises(ModelLoadFailedError):
        await downloader.download_manifest(manifest)


@pytest.mark.asyncio
async def test_downloader_verifies_checksum(tmp_path, monkeypatch):
    data = b"good"
    digest = hashlib.sha256(data).hexdigest()

    def fake_download(repo_id, filename, revision, cache_dir=None, **kwargs):
        out = tmp_path / filename
        out.write_bytes(b"bad")
        return str(out)

    fake_hub = type("M", (), {"hf_hub_download": staticmethod(fake_download)})
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)

    manifest = ModelManifest(
        repo_id="org/repo",
        revision="sha",
        files=(ModelFile(filename="f", expected_sha256=digest),),
    )
    downloader = ModelDownloader(cache_dir=tmp_path)
    with pytest.raises(ModelLoadFailedError):
        await downloader.download_manifest(manifest)


@pytest.mark.asyncio
async def test_downloader_empty_manifest_returns_empty():
    manifest = ModelManifest(repo_id="x", revision="sha", files=())
    downloader = ModelDownloader()
    assert await downloader.download_manifest(manifest) == []


@pytest.mark.asyncio
async def test_default_artifacts_use_pinned_snapshots_and_cache_first(tmp_path, monkeypatch):
    calls = []

    def fake_snapshot_download(
        *, repo_id, revision, cache_dir, allow_patterns, local_files_only
    ):
        calls.append(
            {
                "repo_id": repo_id,
                "revision": revision,
                "cache_dir": cache_dir,
                "local_files_only": local_files_only,
            }
        )
        snapshot = tmp_path / repo_id.replace("/", "--") / revision
        for filename in allow_patterns:
            path = snapshot / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"model")
        return str(snapshot)

    fake_hub = type("M", (), {"snapshot_download": staticmethod(fake_snapshot_download)})
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)

    artifacts = await ensure_default_model_artifacts(tmp_path / "models")

    assert artifacts.onnx_dir.name == "onnx_int8"
    assert artifacts.codec_dir.is_dir()
    assert [call["local_files_only"] for call in calls] == [True, True]
    assert [call["revision"] for call in calls] == [
        "2da0efab622a1722125991736524f080b751ef5b",
        "ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae",
    ]
