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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('tts_custom_voices')]

    new_cols = [
        ("consent_version", sa.Column("consent_version", sa.String(30), nullable=True)),
        ("provider_id", sa.Column("provider_id", sa.String(30), nullable=True)),
        ("engine_id", sa.Column("engine_id", sa.String(50), nullable=True)),
        ("status", sa.Column("status", sa.String(20), nullable=True)),
        ("duration_seconds", sa.Column("duration_seconds", sa.Float(), nullable=True)),
        ("selected_start_seconds", sa.Column("selected_start_seconds", sa.Float(), nullable=True)),
        ("selected_end_seconds", sa.Column("selected_end_seconds", sa.Float(), nullable=True)),
        ("quality_score", sa.Column("quality_score", sa.Integer(), nullable=True)),
        ("analysis_warnings", sa.Column("analysis_warnings", sa.Text(), nullable=True)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for col_name, col_obj in new_cols:
        if col_name not in columns:
            op.add_column("tts_custom_voices", col_obj)

    op.execute("UPDATE tts_custom_voices SET consent_version = 'legacy', provider_id = 'vieneu', engine_id = 'v3turbo', status = 'ready' WHERE consent_version IS NULL")
    # SQLite cannot ALTER COLUMN to add a default/not-null constraint. Legacy
    # rows are backfilled above; new writes are protected by ORM defaults and
    # the orchestrator's explicit values.


def downgrade() -> None:
    for column in ("updated_at", "analysis_warnings", "quality_score", "selected_end_seconds", "selected_start_seconds", "duration_seconds", "status", "engine_id", "provider_id", "consent_version"):
        op.drop_column("tts_custom_voices", column)
