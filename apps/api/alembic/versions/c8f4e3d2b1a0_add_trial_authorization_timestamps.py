"""record compute authorization at request acceptance"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "c8f4e3d2b1a0"
down_revision: str | Sequence[str] | None = "b7e3d2f1a9c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("tts_jobs", "trial_authorized_at"):
        op.add_column("tts_jobs", sa.Column("trial_authorized_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("script_renders", "trial_authorized_at"):
        op.add_column("script_renders", sa.Column("trial_authorized_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    if _has_column("script_renders", "trial_authorized_at"):
        op.drop_column("script_renders", "trial_authorized_at")
    if _has_column("tts_jobs", "trial_authorized_at"):
        op.drop_column("tts_jobs", "trial_authorized_at")
