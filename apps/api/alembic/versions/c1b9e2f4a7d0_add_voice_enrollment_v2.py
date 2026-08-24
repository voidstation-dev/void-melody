"""add voice enrollment v2 columns to tts_custom_voices

Revision ID: c1b9e2f4a7d0
Revises: e8f2c1b9a7d3
Create Date: 2026-08-24
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op


revision: str = "c1b9e2f4a7d0"
down_revision: str | Sequence[str] | None = "e8f2c1b9a7d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tts_custom_voices") as batch_op:
        batch_op.add_column(
            sa.Column("profile_format_version", sa.String(30), server_default="reference-v1", nullable=False)
        )
        batch_op.add_column(
            sa.Column("enrollment_artifact_path", sa.String(1024), nullable=True)
        )
        batch_op.add_column(
            sa.Column("cleaned_reference_audio_path", sa.String(1024), nullable=True)
        )
        batch_op.add_column(
            sa.Column("calibration_audio_path", sa.String(1024), nullable=True)
        )
        batch_op.add_column(
            sa.Column("engine_version", sa.String(50), nullable=True)
        )
        batch_op.add_column(
            sa.Column("reference_fingerprint", sa.String(64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("denoise_mode", sa.String(20), server_default="auto", nullable=False)
        )
        batch_op.add_column(
            sa.Column("denoise_applied", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("clone_mode", sa.String(20), server_default="fidelity", nullable=False)
        )
        batch_op.add_column(
            sa.Column("speaker_similarity_score", sa.Float(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("calibration_quality_score", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("enrollment_created_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("tts_custom_voices") as batch_op:
        batch_op.drop_column("enrollment_created_at")
        batch_op.drop_column("calibration_quality_score")
        batch_op.drop_column("speaker_similarity_score")
        batch_op.drop_column("clone_mode")
        batch_op.drop_column("denoise_applied")
        batch_op.drop_column("denoise_mode")
        batch_op.drop_column("reference_fingerprint")
        batch_op.drop_column("engine_version")
        batch_op.drop_column("calibration_audio_path")
        batch_op.drop_column("cleaned_reference_audio_path")
        batch_op.drop_column("enrollment_artifact_path")
        batch_op.drop_column("profile_format_version")
