"""add Voice Lab profile metadata

Revision ID: 8b7f2c9d4e1a
Revises: 1570f2fe225e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b7f2c9d4e1a"
down_revision: Union[str, Sequence[str], None] = "1570f2fe225e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tts_custom_voices", sa.Column("consent_version", sa.String(30), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("provider_id", sa.String(30), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("engine_id", sa.String(50), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("status", sa.String(20), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("selected_start_seconds", sa.Float(), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("selected_end_seconds", sa.Float(), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("quality_score", sa.Integer(), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("analysis_warnings", sa.Text(), nullable=True))
    op.add_column("tts_custom_voices", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE tts_custom_voices SET consent_version = 'legacy', provider_id = 'vieneu', engine_id = 'v3turbo', status = 'ready' WHERE consent_version IS NULL")
    # SQLite cannot ALTER COLUMN to add a default/not-null constraint. Legacy
    # rows are backfilled above; new writes are protected by ORM defaults and
    # the orchestrator's explicit values.


def downgrade() -> None:
    for column in ("updated_at", "analysis_warnings", "quality_score", "selected_end_seconds", "selected_start_seconds", "duration_seconds", "status", "engine_id", "provider_id", "consent_version"):
        op.drop_column("tts_custom_voices", column)
