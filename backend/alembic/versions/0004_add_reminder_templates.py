"""add reminder templates table

Revision ID: 0004_add_reminder_templates
Revises: c724df95c42a
Create Date: 2026-04-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0004_add_reminder_templates'
down_revision: Union[str, None] = 'c724df95c42a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reminder_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('audio_filename', sa.Text(), nullable=False),
        sa.Column('recurrence', sa.String(20), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('retry_gap_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['SHR_V1.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='SHR_V1',
    )
    op.create_index('ix_reminder_templates_user_id', 'reminder_templates', ['user_id'], schema='SHR_V1')


def downgrade() -> None:
    op.drop_index('ix_reminder_templates_user_id', table_name='reminder_templates', schema='SHR_V1')
    op.drop_table('reminder_templates', schema='SHR_V1')
