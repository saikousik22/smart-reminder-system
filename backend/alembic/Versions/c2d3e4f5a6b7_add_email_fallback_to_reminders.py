"""add email fallback fields to reminders

Revision ID: c2d3e4f5a6b7
Revises: b1a2c3d4e5f6
Create Date: 2026-04-28 00:01:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1a2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'reminders',
        sa.Column('fallback_type', sa.String(length=10), nullable=True),
        schema='SHR_V1',
    )
    op.add_column(
        'reminders',
        sa.Column('fallback_email', sa.String(length=255), nullable=True),
        schema='SHR_V1',
    )


def downgrade() -> None:
    op.drop_column('reminders', 'fallback_email', schema='SHR_V1')
    op.drop_column('reminders', 'fallback_type', schema='SHR_V1')
