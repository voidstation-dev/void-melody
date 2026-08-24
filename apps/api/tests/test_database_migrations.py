import logging
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from app.database import Base, create_database_engine
from app.services.database_migrations import (
    MigrationError,
    run_database_migrations,
)

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"
HEAD_REVISION = "c1b9e2f4a7d0"


def sqlite_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


@pytest.mark.asyncio
async def test_sqlite_engine_enables_required_pragmas(tmp_path):
    engine = create_database_engine(sqlite_url(tmp_path / "pragmas.db"))
    try:
        async with engine.connect() as connection:
            journal_mode = (
                await connection.execute(text("PRAGMA journal_mode"))
            ).scalar_one()
            synchronous = (
                await connection.execute(text("PRAGMA synchronous"))
            ).scalar_one()
            busy_timeout = (
                await connection.execute(text("PRAGMA busy_timeout"))
            ).scalar_one()
            foreign_keys = (
                await connection.execute(text("PRAGMA foreign_keys"))
            ).scalar_one()

        assert journal_mode.lower() == "wal"
        assert synchronous == 1
        assert busy_timeout == 5000
        assert foreign_keys == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_migrations_create_fresh_database(tmp_path):
    database_path = tmp_path / "fresh.db"

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert "tts_jobs" in tables
    with sqlite3.connect(database_path) as connection:
        custom_voice_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(tts_custom_voices)")
        }
    assert {"source_duration_seconds", "reference_duration_seconds"}.issubset(
        custom_voice_columns
    )
    assert revision == HEAD_REVISION


@pytest.mark.asyncio
async def test_voice_duration_migration_preserves_source_and_bounded_reference(tmp_path):
    database_path = tmp_path / "voice-duration.db"

    from alembic import command
    from alembic.config import Config
    from app.services.database_migrations import _sync_database_url

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )
    config = Config(str(ALEMBIC_INI))
    sync_database_url = _sync_database_url(sqlite_url(database_path))
    config.set_main_option("sqlalchemy.url", sync_database_url)
    config.attributes["database_url"] = sync_database_url
    config.attributes["configure_logger"] = False
    command.downgrade(config, "8b7f2c9d4e1a")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO tts_custom_voices
                (id, display_name, reference_audio_path, transcript,
                 consent_given, consent_version, provider_id, engine_id,
                 status, duration_seconds, selected_start_seconds,
                 selected_end_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-voice",
                "Legacy voice",
                "/safe/reference.wav",
                "hello",
                1,
                "voice-lab-v1",
                "vieneu",
                "v3turbo",
                "ready",
                30.0,
                0.0,
                6.0,
                "2026-08-01T00:00:00Z",
            ),
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT duration_seconds, source_duration_seconds, "
            "reference_duration_seconds FROM tts_custom_voices WHERE id = ?",
            ("legacy-voice",),
        ).fetchone()

    assert row == (6.0, 30.0, 6.0)


@pytest.mark.asyncio
async def test_runtime_migration_preserves_application_logging(tmp_path):
    database_path = tmp_path / "logging.db"
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    marker_handler = logging.NullHandler()
    root_logger.handlers = [marker_handler]
    try:
        await run_database_migrations(
            database_url=sqlite_url(database_path),
            alembic_ini_path=ALEMBIC_INI,
        )

        assert root_logger.handlers == [marker_handler]
    finally:
        root_logger.handlers = original_handlers


def create_legacy_database(
    database_path: Path,
    *,
    id_definition: str = "id VARCHAR(36) PRIMARY KEY",
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            f"""
            CREATE TABLE tts_jobs (
                {id_definition},
                kind VARCHAR(20) NOT NULL,
                text TEXT NOT NULL,
                text_hash VARCHAR(64) NOT NULL,
                voice_type VARCHAR(100) NOT NULL,
                voice_display_name VARCHAR(150) NOT NULL,
                resource_id VARCHAR(100),
                language_code VARCHAR(20) NOT NULL,
                rate FLOAT NOT NULL,
                status VARCHAR(20) NOT NULL,
                progress INTEGER,
                provider_task_id VARCHAR(100),
                provider_token VARCHAR(255),
                audio_path VARCHAR(255),
                audio_mime_type VARCHAR(50),
                audio_file_size INTEGER,
                raw_response_path VARCHAR(255),
                error_code VARCHAR(50),
                error_message TEXT,
                attempt_count INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                completed_at DATETIME
            );
            """
        )


@pytest.mark.asyncio
async def test_migrations_adopt_pre_batch_database_and_create_backup(tmp_path):
    database_path = tmp_path / "legacy.db"
    create_legacy_database(database_path)

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert {
        "batch_id",
        "batch_position",
        "source_file_name",
        "source_file_size",
        "cancel_requested",
        "started_at",
    }.issubset(columns)
    assert revision == HEAD_REVISION
    assert len(list(tmp_path.glob("legacy.db.pre-migration-*.bak"))) == 1


@pytest.mark.asyncio
async def test_migrations_adopt_current_unversioned_schema(tmp_path):
    database_path = tmp_path / "current.db"
    engine = create_database_engine(sqlite_url(database_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert revision == HEAD_REVISION


@pytest.mark.asyncio
async def test_migrations_adopt_emotional_script_schema_at_previous_revision(tmp_path):
    """A DB with script tables created before their Alembic revision is stamped
    must not attempt to create those tables a second time on startup.
    """
    database_path = tmp_path / "emotional_script_previous_revision.db"
    from app.models import emotional_script, tts_job  # noqa: F401

    engine = create_database_engine(sqlite_url(database_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
        )
        connection.execute(
            "INSERT INTO alembic_version (version_num) VALUES (?)",
            ("f4a8b6c2d1e0",),
        )
        connection.commit()

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert revision == HEAD_REVISION


@pytest.mark.asyncio
async def test_migrations_reject_unrecognized_legacy_schema(tmp_path):
    database_path = tmp_path / "invalid.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE tts_jobs (id VARCHAR(36) PRIMARY KEY)")

    with pytest.raises(MigrationError, match="missing required columns"):
        await run_database_migrations(
            database_url=sqlite_url(database_path),
            alembic_ini_path=ALEMBIC_INI,
        )


@pytest.mark.asyncio
async def test_migrations_reject_legacy_schema_with_wrong_core_type(tmp_path):
    database_path = tmp_path / "wrong-type.db"
    create_legacy_database(
        database_path,
        id_definition="id INTEGER PRIMARY KEY",
    )

    with pytest.raises(MigrationError, match="incompatible core column"):
        await run_database_migrations(
            database_url=sqlite_url(database_path),
            alembic_ini_path=ALEMBIC_INI,
        )

    assert not list(tmp_path.glob("wrong-type.db.pre-migration-*.bak"))


PROVIDER_FIELDS = {
    "provider_id",
    "backbone_id",
    "style",
    "voice_profile_id",
    "request_metadata",
}


@pytest.mark.asyncio
async def test_migrations_add_provider_fields_to_fresh_database(tmp_path):
    database_path = tmp_path / "fresh_provider.db"

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
    assert PROVIDER_FIELDS.issubset(columns)
    assert revision == HEAD_REVISION


@pytest.mark.asyncio
async def test_migrations_backfill_existing_rows_with_capcut_provider_id(tmp_path):
    database_path = tmp_path / "legacy_rows.db"
    # Build a pre-batch legacy DB with one row, then migrate.
    create_legacy_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO tts_jobs (id, kind, text, text_hash, voice_type, "
            "voice_display_name, language_code, rate, status, attempt_count, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "job-legacy-1",
                "generation",
                "hello",
                "hash-1",
                "BV421_vivn_streaming",
                "Voice",
                "vi-VN",
                1.0,
                "completed",
                0,
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
        connection.commit()

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, provider_id, audio_path FROM tts_jobs WHERE id = ?",
            ("job-legacy-1",),
        ).fetchone()
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
    assert row[0] == "job-legacy-1"  # ID unchanged
    assert row[1] == "capcut"  # backfilled via server_default
    assert row[2] is None  # audio_path unchanged
    assert PROVIDER_FIELDS.issubset(columns)


@pytest.mark.asyncio
async def test_migrations_adopt_current_unversioned_schema_with_provider_fields(
    tmp_path,
):
    """An unversioned schema created by Base.metadata.create_all (which now
    includes the provider fields) must be stamped at head, not adopted as
    legacy (which would try to re-add columns and fail)."""
    database_path = tmp_path / "current_unversioned.db"
    engine = create_database_engine(sqlite_url(database_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    with sqlite3.connect(database_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
    assert revision == HEAD_REVISION
    assert PROVIDER_FIELDS.issubset(columns)


@pytest.mark.asyncio
async def test_migrations_downgrade_drops_provider_fields(tmp_path):
    database_path = tmp_path / "downgrade.db"

    await run_database_migrations(
        database_url=sqlite_url(database_path),
        alembic_ini_path=ALEMBIC_INI,
    )

    from alembic.config import Config

    from alembic import command
    from app.services.database_migrations import _sync_database_url

    config = Config(str(ALEMBIC_INI))
    config.set_main_option(
        "sqlalchemy.url", _sync_database_url(sqlite_url(database_path))
    )
    config.attributes["database_url"] = _sync_database_url(sqlite_url(database_path))
    config.attributes["configure_logger"] = False
    # Downgrade to the previous revision (1ccaccfcb3f0) should drop provider fields.
    command.downgrade(config, "1ccaccfcb3f0")

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tts_jobs)")}
    assert not (PROVIDER_FIELDS & columns)
