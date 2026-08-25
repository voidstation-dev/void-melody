import time
from pathlib import Path


def cleanup_job_artifacts(job_id: str, *, audio_dir: Path) -> list[Path]:
    candidates: set[Path] = set()
    for pattern in (
        f"{job_id}_part*.mp3",
        f"{job_id}_part*.wav",
        f"{job_id}_list.txt",
        f"{job_id}*concat_list.txt",
        f"{job_id}*.tmp*",
    ):
        candidates.update(audio_dir.glob(pattern))

    removed: list[Path] = []
    for path in sorted(candidates):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
        removed.append(path)
    return removed


def cleanup_stale_temp_files(
    *,
    audio_dir: Path,
    older_than_seconds: float = 3_600,
    now: float | None = None,
) -> list[Path]:
    current_time = time.time() if now is None else now
    candidates: set[Path] = set()
    for pattern in ("*_part*.mp3", "*_list.txt", "*.tmp"):
        candidates.update(audio_dir.glob(pattern))

    removed: list[Path] = []
    for path in sorted(candidates):
        try:
            if current_time - path.stat().st_mtime <= older_than_seconds:
                continue
            path.unlink()
        except (FileNotFoundError, OSError):
            continue
        removed.append(path)
    return removed
