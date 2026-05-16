"""add is_deleted to reminders

Revision ID: b1a2c3d4e5f6
Revises: 171bbe9d0e08
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = '171bbe9d0e08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'reminders',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        schema='SHR_V1',
    )
    op.create_index(
        'ix_reminders_is_deleted',
        'reminders',
        ['is_deleted'],
        unique=False,
        schema='SHR_V1',
    )


def downgrade() -> None:
    op.drop_index('ix_reminders_is_deleted', table_name='reminders', schema='SHR_V1')
    op.drop_column('reminders', 'is_deleted', schema='SHR_V1')
