"""add tts_omnivoice_voices table

Revision ID: 84e732c1e05e
Revises: c1b9e2f4a7d0
Create Date: 2026-08-26 13:44:53.654173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84e732c1e05e'
down_revision: Union[str, Sequence[str], None] = 'c1b9e2f4a7d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the provider-specific OmniVoice voice table."""
    op.create_table(
        'tts_omnivoice_voices',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('provider_id', sa.String(length=30), server_default='omnivoice', nullable=False),
        sa.Column('engine_id', sa.String(length=50), server_default='g-omnivoice', nullable=False),
        sa.Column('voice_kind', sa.String(length=20), server_default='design', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='ready', nullable=False),
        sa.Column('design_prompt', sa.Text(), nullable=True),
        sa.Column('compiled_instruction', sa.Text(), nullable=True),
        sa.Column('design_attributes_json', sa.Text(), nullable=True),
        sa.Column('preview_text', sa.Text(), nullable=True),
        sa.Column('selected_preview_audio_path', sa.String(length=1024), nullable=True),
        sa.Column('prompt_artifact_path', sa.String(length=1024), nullable=False),
        sa.Column('prompt_format_version', sa.String(length=50), server_default='omnivoice-voice-clone-prompt', nullable=False),
        sa.Column('model_id', sa.String(length=50), server_default='g-omnivoice', nullable=False),
        sa.Column('model_revision', sa.String(length=50), server_default='2025-08-20-a', nullable=False),
        sa.Column('engine_version', sa.String(length=50), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('voice_revision', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tts_omnivoice_voices_provider_id'), 'tts_omnivoice_voices', ['provider_id'], unique=False)
    op.create_index(op.f('ix_tts_omnivoice_voices_status'), 'tts_omnivoice_voices', ['status'], unique=False)
    op.create_index(op.f('ix_tts_omnivoice_voices_voice_kind'), 'tts_omnivoice_voices', ['voice_kind'], unique=False)


def downgrade() -> None:
    """Drop the OmniVoice voice table."""
    op.drop_index(op.f('ix_tts_omnivoice_voices_voice_kind'), table_name='tts_omnivoice_voices')
    op.drop_index(op.f('ix_tts_omnivoice_voices_status'), table_name='tts_omnivoice_voices')
    op.drop_index(op.f('ix_tts_omnivoice_voices_provider_id'), table_name='tts_omnivoice_voices')
    op.drop_table('tts_omnivoice_voices')
