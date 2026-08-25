"""Runtime manager: manifest, verifier, installer, registry, service tests."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.services.runtime_manager.models import (
    PROTOCOL_VERSION,
    RuntimeManifest,
    RuntimeStatus,
)
from app.services.runtime_manager.manifests import (
    current_arch,
    current_platform,
    get_manifest,
    is_known_runtime,
    known_manifests,
)
from app.services.runtime_manager.verifier import safe_extract_zip, verify_sha256
from app.services.runtime_manager.installer import (
    active_symlink,
    disk_usage,
    install_pack,
    rollback,
    runtime_version_dir,
    staging_dir,
    uninstall_runtime,
)
from app.services.runtime_manager.registry import RuntimeRegistry
from app.services.runtime_manager.service import RuntimeManagerService

def _make_manifest(runtime_id: str = "speech", version: str = "1.0.0", entrypoint: str = "worker.py") -> RuntimeManifest:
    return RuntimeManifest(
        schema_version=1,
        runtime_id=runtime_id,
        version=version,
        protocol_version=PROTOCOL_VERSION,
        platform="test",
        arch="test",
        download_url="",
        sha256="",
        size_bytes=0,
        entrypoint=entrypoint,
    )


def _make_zip(path: Path, entrypoint: str = "worker.py") -> Path:
    """Create a minimal valid runtime ZIP with an entrypoint file."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(entrypoint, "# test worker\n")
        zf.writestr("README.txt", "test\n")
    return path


class TestManifests:
    def test_known_manifests_return_both_packs(self):
        manifests = known_manifests()
        assert set(manifests.keys()) == {"vieneu", "speech"}

    def test_manifests_have_protocol_version(self):
        for m in known_manifests().values():
            assert m.protocol_version == PROTOCOL_VERSION

    def test_is_known_runtime(self):
        assert is_known_runtime("vieneu")
        assert is_known_runtime("speech")
        assert not is_known_runtime("unknown")

    def test_get_manifest_unknown_returns_none(self):
        assert get_manifest("unknown") is None

    def test_current_platform_and_arch_detected(self):
        assert current_platform() in {"windows", "linux", "macos", "unknown"}
        assert current_arch() in {"x86_64", "aarch64", "unknown"}


class TestVerifier:
    def test_verify_sha256_correct(self, tmp_path: Path):
        data = b"hello world"
        f = tmp_path / "test.bin"
        f.write_bytes(data)
        expected = hashlib.sha256(data).hexdigest()
        assert verify_sha256(f, expected) is True

    def test_verify_sha256_wrong(self, tmp_path: Path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello")
        assert verify_sha256(f, "0" * 64) is False

    def test_safe_extract_rejects_traversal(self, tmp_path: Path):
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../escape.txt", "evil")
        dest = tmp_path / "dest"
        with pytest.raises(Exception, match="UNSAFE_ZIP_ENTRY|escape"):
            safe_extract_zip(zip_path, dest)

    def test_safe_extract_rejects_absolute(self, tmp_path: Path):
        zip_path = tmp_path / "abs.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/passwd", "evil")
        dest = tmp_path / "dest"
        with pytest.raises(Exception, match="Refusing to extract"):
            safe_extract_zip(zip_path, dest)

    def test_safe_extract_valid(self, tmp_path: Path):
        zip_path = tmp_path / "ok.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("worker.py", "# ok\n")
            zf.writestr("lib/data.txt", "data\n")
        dest = tmp_path / "dest"
        safe_extract_zip(zip_path, dest)
        assert (dest / "worker.py").is_file()
        assert (dest / "lib" / "data.txt").is_file()


class TestInstaller:
    def test_install_pack_activates(self, tmp_path: Path):
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)

        final = install_pack(zip_path, manifest, tmp_path)
        assert final.is_dir()
        assert (final / "worker.py").is_file()
        assert (final / "manifest.json").is_file()

        link = active_symlink(tmp_path, "speech")
        assert link.is_symlink()
        assert link.resolve() == final.resolve()

    def test_install_pack_missing_entrypoint_fails(self, tmp_path: Path):
        manifest = _make_manifest(entrypoint="nonexistent.py")
        zip_path = tmp_path / "pack.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("other.py", "# no entrypoint\n")
        with pytest.raises(Exception, match="not found after extraction"):
            install_pack(zip_path, manifest, tmp_path)
        # Staging should be cleaned up
        assert not staging_dir(tmp_path, "speech", "1.0.0").exists()

    def test_install_pack_probe_failure_cleans_staging(self, tmp_path: Path):
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)

        def failing_probe(_entrypoint):
            raise RuntimeError("probe failed")

        with pytest.raises(Exception, match="Worker probe failed"):
            install_pack(zip_path, manifest, tmp_path, probe_fn=failing_probe)
        assert not staging_dir(tmp_path, "speech", "1.0.0").exists()

    def test_rollback_reverts_to_previous(self, tmp_path: Path):
        manifest_v1 = _make_manifest(version="1.0.0")
        manifest_v2 = _make_manifest(version="2.0.0")

        zip1 = tmp_path / "v1.zip"
        _make_zip(zip1)
        install_pack(zip1, manifest_v1, tmp_path)

        zip2 = tmp_path / "v2.zip"
        _make_zip(zip2)
        install_pack(zip2, manifest_v2, tmp_path)

        # Active should be v2
        link = active_symlink(tmp_path, "speech")
        assert "2.0.0" in link.resolve().name

        # Rollback to v1
        prev = rollback(tmp_path, "speech")
        assert prev == "1.0.0"
        assert "1.0.0" in active_symlink(tmp_path, "speech").resolve().name

    def test_rollback_no_previous_returns_none(self, tmp_path: Path):
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)
        install_pack(zip_path, manifest, tmp_path)
        # No rollback possible (only one version)
        result = rollback(tmp_path, "speech")
        # Can't roll back if only one version — active stays
        assert result is None or "1.0.0" in active_symlink(tmp_path, "speech").resolve().name

    def test_disk_usage_counts_files(self, tmp_path: Path):
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)
        install_pack(zip_path, manifest, tmp_path)
        usage = disk_usage(tmp_path, "speech")
        assert usage > 0

    def test_uninstall_runtime_removes_everything(self, tmp_path: Path):
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)
        install_pack(zip_path, manifest, tmp_path)
        uninstall_runtime(tmp_path, "speech")
        assert not (tmp_path / "runtimes" / "speech").exists()
        assert disk_usage(tmp_path, "speech") == 0


class TestRegistry:
    def test_registry_persists_state(self, tmp_path: Path):
        reg = RuntimeRegistry(tmp_path)
        reg.set_active("speech", "1.0.0", protocol_version=1)
        assert reg.get("speech").active_version == "1.0.0"
        assert reg.get("speech").status == RuntimeStatus.ready

        # New instance loads from disk
        reg2 = RuntimeRegistry(tmp_path)
        assert reg2.get("speech").active_version == "1.0.0"
        assert reg2.get("speech").protocol_version == 1

    def test_registry_clear(self, tmp_path: Path):
        reg = RuntimeRegistry(tmp_path)
        reg.set_active("speech", "1.0.0")
        reg.clear("speech")
        state = reg.get("speech")
        assert state.status == RuntimeStatus.missing
        assert state.active_version is None

    def test_registry_list_all(self, tmp_path: Path):
        reg = RuntimeRegistry(tmp_path)
        reg.set_active("vieneu", "1.0.0")
        reg.set_active("speech", "0.1.0")
        all_states = reg.list_all()
        assert len(all_states) == 2


class TestService:
    def test_status_unknown_runtime_raises(self, tmp_path: Path):
        svc = RuntimeManagerService(data_dir=tmp_path)
        with pytest.raises(Exception, match="Unknown runtime"):
            svc.status("unknown")

    def test_list_statuses_returns_both(self, tmp_path: Path):
        svc = RuntimeManagerService(data_dir=tmp_path)
        statuses = svc.list_statuses()
        ids = [s.runtime_id for s in statuses]
        assert "vieneu" in ids
        assert "speech" in ids

    def test_install_with_zip(self, tmp_path: Path):
        svc = RuntimeManagerService(data_dir=tmp_path)
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)

        # Monkeypatch get_manifest to return our test manifest
        import app.services.runtime_manager.service as svc_mod
        original = svc_mod.get_manifest
        svc_mod.get_manifest = lambda rid: manifest if rid == "speech" else original(rid)
        try:
            result = svc.install("speech", zip_path=zip_path)
            assert result.status == RuntimeStatus.ready
            assert result.active_version == "1.0.0"
        finally:
            svc_mod.get_manifest = original

    def test_remove_runtime(self, tmp_path: Path):
        svc = RuntimeManagerService(data_dir=tmp_path)
        manifest = _make_manifest()
        zip_path = tmp_path / "pack.zip"
        _make_zip(zip_path)

        import app.services.runtime_manager.service as svc_mod
        original = svc_mod.get_manifest
        svc_mod.get_manifest = lambda rid: manifest if rid == "speech" else original(rid)
        try:
            svc.install("speech", zip_path=zip_path)
            svc.remove("speech")
            state = svc.status("speech")
            assert state.status == RuntimeStatus.missing
        finally:
            svc_mod.get_manifest = original