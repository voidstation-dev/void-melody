"""add audio segment cache and optimization workload indexes

Revision ID: e8f2c1b9a7d3
Revises: b7e3d2f1a9c4
Create Date: 2026-08-24
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op


revision: str = "e8f2c1b9a7d3"
down_revision: str | Sequence[str] | None = "b7e3d2f1a9c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create generic audio_segment_cache table
    op.create_table(
        "audio_segment_cache",
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("provider_id", sa.String(30), nullable=False),
        sa.Column("provider_version", sa.String(30), nullable=False, server_default="v1"),
        sa.Column("voice_key", sa.String(100), nullable=False),
        sa.Column("voice_revision", sa.String(100), nullable=False, server_default="v1"),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("style", sa.String(50), nullable=True),
        sa.Column("rate", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("audio_path", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default="audio/mpeg"),
        sa.Column("audio_duration", sa.Float(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("fingerprint"),
    )
    op.create_index("ix_audio_segment_cache_last_used", "audio_segment_cache", ["last_used_at"])
    op.create_index("ix_audio_segment_cache_voice_key", "audio_segment_cache", ["voice_key"])

    # 2. Add workload composite indexes
    op.create_index(
        "ix_tts_jobs_status_created_id",
        "tts_jobs",
        ["status", "created_at", "id"],
    )
    op.create_index(
        "ix_tts_jobs_batch_position",
        "tts_jobs",
        ["batch_id", "batch_position"],
    )
    op.create_index(
        "ix_script_segments_render_ordinal",
        "script_render_segments",
        ["render_id", "ordinal"],
    )

    # 3. Add partial index for active jobs in SQLite
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tts_jobs_active_created "
        "ON tts_jobs (created_at) WHERE status IN ('queued', 'processing')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tts_jobs_active_created")
    op.drop_index("ix_script_segments_render_ordinal", table_name="script_render_segments")
    op.drop_index("ix_tts_jobs_batch_position", table_name="tts_jobs")
    op.drop_index("ix_tts_jobs_status_created_id", table_name="tts_jobs")
    op.drop_index("ix_audio_segment_cache_voice_key", table_name="audio_segment_cache")
    op.drop_index("ix_audio_segment_cache_last_used", table_name="audio_segment_cache")
    op.drop_table("audio_segment_cache")
