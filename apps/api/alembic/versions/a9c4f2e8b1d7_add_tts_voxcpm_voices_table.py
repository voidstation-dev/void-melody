"""add tts_voxcpm_voices table

Revision ID: a9c4f2e8b1d7
Revises: d356ea30efdd
Create Date: 2026-09-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9c4f2e8b1d7'
down_revision: Union[str, Sequence[str], None] = 'd356ea30efdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the provider-specific VoxCPM2 voice table."""
    op.create_table(
        'tts_voxcpm_voices',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('provider_id', sa.String(length=30), server_default='voxcpm2', nullable=False),
        sa.Column('engine_id', sa.String(length=50), server_default='voxcpm2', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='ready', nullable=False),
        sa.Column('reference_audio_path', sa.String(length=1024), nullable=False),
        sa.Column('reference_original_filename', sa.String(length=255), nullable=True),
        sa.Column('reference_duration_seconds', sa.Float(), nullable=True),
        sa.Column('reference_sample_rate', sa.Integer(), nullable=True),
        sa.Column('reference_channels', sa.Integer(), nullable=True),
        sa.Column('reference_transcript', sa.Text(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('speech_ratio', sa.Float(), nullable=True),
        sa.Column('noise_level_db', sa.Float(), nullable=True),
        sa.Column('clipping_ratio', sa.Float(), nullable=True),
        sa.Column('model_id', sa.String(length=100), server_default='openbmb/VoxCPM2', nullable=False),
        sa.Column('model_revision', sa.String(length=50), server_default='main', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tts_voxcpm_voices_provider_id'), 'tts_voxcpm_voices', ['provider_id'], unique=False)
    op.create_index(op.f('ix_tts_voxcpm_voices_status'), 'tts_voxcpm_voices', ['status'], unique=False)


def downgrade() -> None:
    """Drop the VoxCPM2 voice table."""
    op.drop_index(op.f('ix_tts_voxcpm_voices_status'), table_name='tts_voxcpm_voices')
    op.drop_index(op.f('ix_tts_voxcpm_voices_provider_id'), table_name='tts_voxcpm_voices')
    op.drop_table('tts_voxcpm_voices')