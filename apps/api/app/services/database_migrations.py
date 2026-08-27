import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from alembic import command
from app.config import settings

BASELINE_REVISION = "37c7b24d235a"
EMOTIONAL_SCRIPT_PREVIOUS_REVISION = "f4a8b6c2d1e0"
LEGACY_CORE_COLUMNS = {
    "id",
    "kind",
    "text",
    "text_hash",
    "voice_type",
    "voice_display_name",
    "resource_id",
    "language_code",
    "rate",
    "status",
    "progress",
    "provider_task_id",
    "provider_token",
    "audio_path",
    "audio_mime_type",
    "audio_file_size",
    "raw_response_path",
    "error_code",
    "error_message",
    "attempt_count",
    "created_at",
    "updated_at",
    "completed_at",
}
LEGACY_CORE_SCHEMA = {
    "id": ("VARCHAR(36)", None, 1),
    "kind": ("VARCHAR(20)", True, 0),
    "text": ("TEXT", True, 0),
    "text_hash": ("VARCHAR(64)", True, 0),
    "voice_type": ("VARCHAR(100)", True, 0),
    "voice_display_name": ("VARCHAR(150)", True, 0),
    "resource_id": ("VARCHAR(100)", False, 0),
    "language_code": ("VARCHAR(20)", True, 0),
    "rate": ("FLOAT", True, 0),
    "status": ("VARCHAR(20)", True, 0),
    "progress": ("INTEGER", False, 0),
    "provider_task_id": ("VARCHAR(100)", False, 0),
    "provider_token": ("VARCHAR(255)", False, 0),
    "audio_path": ("VARCHAR(255)", False, 0),
    "audio_mime_type": ("VARCHAR(50)", False, 0),
    "audio_file_size": ("INTEGER", False, 0),
    "raw_response_path": ("VARCHAR(255)", False, 0),
    "error_code": ("VARCHAR(50)", False, 0),
    "error_message": ("TEXT", False, 0),
    "attempt_count": ("INTEGER", True, 0),
    "created_at": ("DATETIME", True, 0),
    "updated_at": ("DATETIME", True, 0),
    "completed_at": ("DATETIME", False, 0),
}
LEGACY_ADDITIONS = {
    "batch_id": "VARCHAR(36)",
    "batch_position": "INTEGER",
    "source_file_name": "VARCHAR(255)",
    "source_file_size": "INTEGER",
    "cancel_requested": "BOOLEAN NOT NULL DEFAULT 0",
    "started_at": "DATETIME",
}
# Columns introduced by migrations after BASELINE_REVISION. An unversioned
# schema that already contains all of these matches the current model metadata
# (e.g. created by Base.metadata.create_all) and must be stamped at head rather
# than adopted as legacy, otherwise the head migration would try to re-add the
# column and fail with "duplicate column name".
POST_BASELINE_COLUMNS = {
    "audio_duration",
    "provider_id",
    "backbone_id",
    "style",
    "voice_profile_id",
    "request_metadata",
    "export_path",
    "export_format",
}
POST_BASELINE_CUSTOM_VOICE_COLUMNS = {
    "source_duration_seconds",
    "reference_duration_seconds",
    "profile_format_version",
    "enrollment_artifact_path",
    "cleaned_reference_audio_path",
    "calibration_audio_path",
    "engine_version",
    "reference_fingerprint",
    "denoise_mode",
    "denoise_applied",
    "clone_mode",
    "speaker_similarity_score",
    "calibration_quality_score",
    "enrollment_created_at",
}
POST_BASELINE_OMNIVOICE_VOICE_COLUMNS = {
    "license_entitlement_id",
}
OMNIVOICE_VOICE_TABLE = "tts_omnivoice_voices"


class MigrationError(RuntimeError):
    pass


def _sync_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        url = url.set(drivername="sqlite")
    return url.render_as_string(hide_password=False)


def _sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    return Path(url.database).expanduser().resolve()


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        is not None
    )


def _current_revision(connection: sqlite3.Connection) -> str | None:
    if not _table_exists(connection, "alembic_version"):
        return None
    row = connection.execute(
        "SELECT version_num FROM alembic_version LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def _has_post_baseline_columns(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, "tts_jobs"):
        return False
    columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
    if not POST_BASELINE_COLUMNS.issubset(columns):
        return False
    if not _table_exists(connection, "tts_custom_voices"):
        return False
    custom_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(tts_custom_voices)")
    }
    if not POST_BASELINE_CUSTOM_VOICE_COLUMNS.issubset(custom_columns):
        return False
    if not _table_exists(connection, OMNIVOICE_VOICE_TABLE):
        return False
    return True


def _has_emotional_script_tables(connection: sqlite3.Connection) -> bool:
    return all(
        _table_exists(connection, table_name)
        for table_name in (
            "emotional_scripts",
            "script_renders",
            "script_render_segments",
            "script_audio_cache",
        )
    )


def _has_audio_segment_cache_table(connection: sqlite3.Connection) -> bool:
    return _table_exists(connection, "audio_segment_cache")


def _backup_database(database_path: Path, *, retain: int = 3) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = database_path.with_name(
        f"{database_path.name}.pre-migration-{timestamp}.bak"
    )
    with (
        sqlite3.connect(database_path) as source,
        sqlite3.connect(backup_path) as destination,
    ):
        source.backup(destination)

    backups = sorted(
        database_path.parent.glob(f"{database_path.name}.pre-migration-*.bak"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for stale_backup in backups[retain:]:
        stale_backup.unlink(missing_ok=True)
    return backup_path


def _adopt_legacy_schema(
    config: Config,
    database_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        column_rows = list(connection.execute("PRAGMA table_info(tts_jobs)"))
        columns = {row[1] for row in column_rows}
        missing_core = LEGACY_CORE_COLUMNS - columns
        if missing_core:
            missing = ", ".join(sorted(missing_core))
            raise MigrationError(
                f"Legacy tts_jobs schema is missing required columns: {missing}"
            )
        definitions = {
            row[1]: (row[2].upper(), bool(row[3]), row[5]) for row in column_rows
        }
        incompatible = []
        for name, (
            expected_type,
            expected_notnull,
            expected_pk,
        ) in LEGACY_CORE_SCHEMA.items():
            actual_type, actual_notnull, actual_pk = definitions[name]
            if (
                actual_type != expected_type
                or (expected_notnull is not None and actual_notnull != expected_notnull)
                or actual_pk != expected_pk
            ):
                incompatible.append(name)
        if incompatible:
            names = ", ".join(sorted(incompatible))
            raise MigrationError(
                "Legacy tts_jobs schema has incompatible core column "
                f"definitions: {names}"
            )

    _backup_database(database_path)
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
        for name, sql_type in LEGACY_ADDITIONS.items():
            if name not in columns:
                connection.execute(
                    f'ALTER TABLE tts_jobs ADD COLUMN "{name}" {sql_type}'
                )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_tts_jobs_batch_id ON tts_jobs (batch_id)"
        )
        connection.commit()
    command.stamp(config, BASELINE_REVISION)


OPTIMIZATION_PREVIOUS_REVISION = "b7e3d2f1a9c4"
ENROLLMENT_V2_PREVIOUS_REVISION = "e8f2c1b9a7d3"


def _run_database_migrations(
    *,
    database_url: str,
    alembic_ini_path: Path,
) -> None:
    config = Config(str(alembic_ini_path))
    sync_url = _sync_database_url(database_url)
    config.set_main_option("sqlalchemy.url", sync_url)
    config.attributes["database_url"] = sync_url
    config.attributes["configure_logger"] = False
    head_revision = ScriptDirectory.from_config(config).get_current_head()
    database_path = _sqlite_database_path(database_url)

    if database_path is not None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database_path) as connection:
            has_jobs_table = _table_exists(connection, "tts_jobs")
            has_custom_voices = _table_exists(connection, "tts_custom_voices")
            current_revision = _current_revision(connection)
            has_emotional_script_tables = _has_emotional_script_tables(connection)
            has_audio_cache_table = _has_audio_segment_cache_table(connection)
            has_post_baseline = _has_post_baseline_columns(connection)

        if has_jobs_table:
            if has_custom_voices and has_emotional_script_tables and has_audio_cache_table and has_post_baseline:
                if current_revision != head_revision:
                    command.stamp(config, head_revision)
            elif has_custom_voices and has_emotional_script_tables and has_audio_cache_table:
                if current_revision != ENROLLMENT_V2_PREVIOUS_REVISION and current_revision != head_revision:
                    command.stamp(config, ENROLLMENT_V2_PREVIOUS_REVISION)
            elif has_custom_voices and has_emotional_script_tables and has_post_baseline:
                if current_revision != OPTIMIZATION_PREVIOUS_REVISION and current_revision != head_revision:
                    command.stamp(config, OPTIMIZATION_PREVIOUS_REVISION)
            elif has_custom_voices and has_post_baseline:
                if current_revision != EMOTIONAL_SCRIPT_PREVIOUS_REVISION:
                    command.stamp(config, EMOTIONAL_SCRIPT_PREVIOUS_REVISION)
            elif current_revision is None:
                _adopt_legacy_schema(config, database_path)
            elif current_revision != head_revision:
                _backup_database(database_path)

    command.upgrade(config, "head")


async def run_database_migrations(
    *,
    database_url: str | None = None,
    alembic_ini_path: Path | None = None,
) -> None:
    runtime_url = database_url or settings.database_url
    ini_path = alembic_ini_path or (Path(__file__).resolve().parents[2] / "alembic.ini")
    await asyncio.to_thread(
        _run_database_migrations,
        database_url=runtime_url,
        alembic_ini_path=ini_path,
    )
