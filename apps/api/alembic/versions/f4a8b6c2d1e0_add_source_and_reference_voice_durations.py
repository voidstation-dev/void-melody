"""split custom voice source and reference duration metadata"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "f4a8b6c2d1e0"
down_revision: str | Sequence[str] | None = "8b7f2c9d4e1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('tts_custom_voices')]
    if "source_duration_seconds" not in columns:
        op.add_column(
            "tts_custom_voices",
            sa.Column("source_duration_seconds", sa.Float(), nullable=True),
        )
    if "reference_duration_seconds" not in columns:
        op.add_column(
            "tts_custom_voices",
            sa.Column("reference_duration_seconds", sa.Float(), nullable=True),
        )
    op.execute(
        """
        UPDATE tts_custom_voices
        SET source_duration_seconds = duration_seconds,
            reference_duration_seconds = CASE
                WHEN selected_start_seconds IS NOT NULL
                 AND selected_end_seconds IS NOT NULL
                THEN selected_end_seconds - selected_start_seconds
                ELSE duration_seconds
            END
        """
    )
    # Keep the legacy field useful to clients that only know duration_seconds:
    # it now reflects the bounded reference, not the original source upload.
    op.execute(
        """
        UPDATE tts_custom_voices
        SET duration_seconds = reference_duration_seconds
        WHERE reference_duration_seconds IS NOT NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("tts_custom_voices") as batch_op:
        batch_op.drop_column("reference_duration_seconds")
        batch_op.drop_column("source_duration_seconds")
