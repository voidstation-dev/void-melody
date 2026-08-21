import os
from pathlib import Path

from app.services.audio_cleanup import (
    cleanup_job_artifacts,
    cleanup_stale_temp_files,
)
from app.services.voice_artifact_cleanup import cleanup_orphan_voice_artifacts


def test_cleanup_job_artifacts_preserves_final_audio(tmp_path: Path):
    part = tmp_path / "job-1_part0.mp3"
    concat_list = tmp_path / "job-1_list.txt"
    temporary = tmp_path / "job-1.mp3.tmp"
    final = tmp_path / "job-1.mp3"
    for path in (part, concat_list, temporary, final):
        path.write_bytes(b"data")

    cleanup_job_artifacts("job-1", audio_dir=tmp_path)

    assert not part.exists()
    assert not concat_list.exists()
    assert not temporary.exists()
    assert final.exists()


def test_startup_cleanup_only_removes_stale_temporary_files(tmp_path: Path):
    stale = tmp_path / "old_part0.mp3"
    fresh = tmp_path / "fresh_part0.mp3"
    final = tmp_path / "completed.mp3"
    for path in (stale, fresh, final):
        path.write_bytes(b"data")
    os.utime(stale, (100, 100))
    os.utime(fresh, (9_900, 9_900))
    os.utime(final, (100, 100))

    removed = cleanup_stale_temp_files(
        audio_dir=tmp_path,
        older_than_seconds=3_600,
        now=10_000,
    )

    assert removed == [stale]
    assert not stale.exists()
    assert fresh.exists()
    assert final.exists()


def test_voice_cleanup_removes_only_stale_orphaned_profile_artifacts(tmp_path: Path):
    known = tmp_path / "11111111-1111-1111-1111-111111111111.wav"
    orphan = tmp_path / "22222222-2222-2222-2222-222222222222.wav"
    fresh_orphan = tmp_path / "33333333-3333-3333-3333-333333333333.wav"
    known.write_bytes(b"known")
    orphan.write_bytes(b"orphan")
    fresh_orphan.write_bytes(b"fresh")
    uploads = tmp_path / ".uploads"
    uploads.mkdir()
    stale_upload = uploads / "abc.input"
    stale_upload.write_bytes(b"upload")

    for path in (known, orphan, stale_upload):
        os.utime(path, (100, 100))
    os.utime(fresh_orphan, (9_900, 9_900))

    removed = cleanup_orphan_voice_artifacts(
        tmp_path,
        known_paths={known},
        older_than_seconds=3_600,
        now=10_000,
    )

    assert removed == [orphan, stale_upload]
    assert known.exists()
    assert not orphan.exists()
    assert fresh_orphan.exists()
    assert not stale_upload.exists()
