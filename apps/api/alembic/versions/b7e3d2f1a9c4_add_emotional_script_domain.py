"""add isolated Emotional Script domain tables"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7e3d2f1a9c4"
down_revision: str | Sequence[str] | None = "f4a8b6c2d1e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emotional_scripts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("document_json", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emotional_scripts_created_at", "emotional_scripts", ["created_at"])

    op.create_table(
        "script_renders",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("script_id", sa.String(36), nullable=False),
        sa.Column("script_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("stage", sa.String(30), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("total_segments", sa.Integer(), nullable=False),
        sa.Column("cached_segments", sa.Integer(), nullable=False),
        sa.Column("completed_segments", sa.Integer(), nullable=False),
        sa.Column("failed_segments", sa.Integer(), nullable=False),
        sa.Column("output_path", sa.String(1024), nullable=True),
        sa.Column("output_format", sa.String(10), nullable=False),
        sa.Column("output_mime_type", sa.String(50), nullable=True),
        sa.Column("output_duration", sa.Float(), nullable=True),
        sa.Column("output_file_size", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["script_id"], ["emotional_scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_script_renders_script_id", "script_renders", ["script_id"])
    op.create_index("ix_script_renders_status", "script_renders", ["status"])

    op.create_table(
        "script_render_segments",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("render_id", sa.String(36), nullable=False),
        sa.Column("script_id", sa.String(36), nullable=False),
        sa.Column("line_id", sa.String(100), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("voice_id", sa.String(100), nullable=False),
        sa.Column("voice_mode", sa.String(10), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("resolved_request_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("audio_path", sa.String(1024), nullable=True),
        sa.Column("audio_duration", sa.Float(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["render_id"], ["script_renders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["emotional_scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_script_render_segments_render_id", "script_render_segments", ["render_id"])
    op.create_index("ix_script_render_segments_script_id", "script_render_segments", ["script_id"])
    op.create_index("ix_script_render_segments_request_fingerprint", "script_render_segments", ["request_fingerprint"])
    op.create_index("ix_script_render_segments_status", "script_render_segments", ["status"])

    op.create_table(
        "script_audio_cache",
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("audio_path", sa.String(1024), nullable=False),
        sa.Column("voice_id", sa.String(100), nullable=False),
        sa.Column("voice_mode", sa.String(10), nullable=False),
        sa.Column("audio_duration", sa.Float(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("script_audio_cache")
    op.drop_index("ix_script_render_segments_status", table_name="script_render_segments")
    op.drop_index("ix_script_render_segments_request_fingerprint", table_name="script_render_segments")
    op.drop_index("ix_script_render_segments_script_id", table_name="script_render_segments")
    op.drop_index("ix_script_render_segments_render_id", table_name="script_render_segments")
    op.drop_table("script_render_segments")
    op.drop_index("ix_script_renders_status", table_name="script_renders")
    op.drop_index("ix_script_renders_script_id", table_name="script_renders")
    op.drop_table("script_renders")
    op.drop_index("ix_emotional_scripts_created_at", table_name="emotional_scripts")
    op.drop_table("emotional_scripts")

