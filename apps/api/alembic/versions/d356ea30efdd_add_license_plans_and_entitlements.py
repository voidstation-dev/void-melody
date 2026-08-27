"""add license plans and entitlements

Revision ID: d356ea30efdd
Revises: 84e732c1e05e
Create Date: 2026-08-26 17:36:41.884123

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd356ea30efdd'
down_revision: Union[str, Sequence[str], None] = '84e732c1e05e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FREE_FEATURES = {
    "tts": True,
    "voice_lab": False,
    "voice_design": False,
    "audio_studio": False,
    "transcription": False,
    "runtime_install": False,
    "providers": ["capcut"],
    "max_custom_voices": 0,
    "max_concurrent_jobs": 1,
    "max_batch_files": 5,
}

PRO_FEATURES = {
    "tts": True,
    "voice_lab": True,
    "custom_voices": True,
    "voice_design": True,
    "audio_studio": True,
    "transcription": True,
    "runtime_install": True,
    "providers": ["capcut", "vieneu", "omnivoice"],
    "max_custom_voices": 50,
    "max_concurrent_jobs": 5,
    "max_batch_files": 50,
}

TEAM_FEATURES = {
    **PRO_FEATURES,
    "max_custom_voices": 200,
    "max_concurrent_jobs": 15,
    "max_batch_files": 200,
}

DEFAULT_PLANS = [
    ("free", "Free", "Limited CapCut TTS only.", FREE_FEATURES, 0),
    ("pro", "Pro", "Full access to all providers and voice lab features.", PRO_FEATURES, 10),
    ("team", "Team", "Higher quotas for shared workspaces.", TEAM_FEATURES, 20),
]


def upgrade() -> None:
    """Create license tables, seed default plans, and link existing records."""
    op.create_table(
        'license_plans',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_license_plans_slug'), 'license_plans', ['slug'], unique=True)
    op.create_index(op.f('ix_license_plans_is_active'), 'license_plans', ['is_active'], unique=False)

    op.create_table(
        'license_entitlements',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('license_key', sa.String(length=255), nullable=False),
        sa.Column('plan_id', sa.String(length=36), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['license_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_license_entitlements_license_key'), 'license_entitlements', ['license_key'], unique=False)
    op.create_index(op.f('ix_license_entitlements_is_active'), 'license_entitlements', ['is_active'], unique=False)

    # Add entitlement tracking columns to existing tables (batch mode for SQLite).
    # NOTE: SQLite cannot create named FK constraints via ALTER, so we keep the
    # column nullable without an explicit FK at the migration level. The ORM
    # still validates referential intent; ondelete behavior is enforced by the
    # application for SQLite.
    with op.batch_alter_table('tts_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('license_entitlement_id', sa.String(length=36), nullable=True))
        batch_op.create_index(op.f('ix_tts_jobs_license_entitlement_id'), ['license_entitlement_id'], unique=False)

    with op.batch_alter_table('tts_custom_voices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('license_entitlement_id', sa.String(length=36), nullable=True))
        batch_op.create_index(op.f('ix_tts_custom_voices_license_entitlement_id'), ['license_entitlement_id'], unique=False)

    with op.batch_alter_table('tts_omnivoice_voices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('license_entitlement_id', sa.String(length=36), nullable=True))
        batch_op.create_index(op.f('ix_tts_omnivoice_voices_license_entitlement_id'), ['license_entitlement_id'], unique=False)

    # Seed default plans.
    license_plans = sa.table(
        'license_plans',
        sa.column('id', sa.String),
        sa.column('slug', sa.String),
        sa.column('display_name', sa.String),
        sa.column('description', sa.Text),
        sa.column('is_active', sa.Boolean),
        sa.column('priority', sa.Integer),
        sa.column('features', sa.JSON),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        license_plans,
        [
            {
                "id": str(uuid.uuid4()),
                "slug": slug,
                "display_name": display_name,
                "description": description,
                "is_active": True,
                "priority": priority,
                "features": features,
                "created_at": now,
                "updated_at": now,
            }
            for slug, display_name, description, features, priority in DEFAULT_PLANS
        ],
    )


def downgrade() -> None:
    """Reverse the license schema changes."""
    with op.batch_alter_table('tts_omnivoice_voices', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_tts_omnivoice_voices_license_entitlement_id'))
        batch_op.drop_column('license_entitlement_id')

    with op.batch_alter_table('tts_custom_voices', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_tts_custom_voices_license_entitlement_id'))
        batch_op.drop_column('license_entitlement_id')

    with op.batch_alter_table('tts_jobs', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_tts_jobs_license_entitlement_id'))
        batch_op.drop_column('license_entitlement_id')

    op.drop_index(op.f('ix_license_entitlements_is_active'), table_name='license_entitlements')
    op.drop_index(op.f('ix_license_entitlements_license_key'), table_name='license_entitlements')
    op.drop_table('license_entitlements')

    op.drop_index(op.f('ix_license_plans_is_active'), table_name='license_plans')
    op.drop_index(op.f('ix_license_plans_slug'), table_name='license_plans')
    op.drop_table('license_plans')
