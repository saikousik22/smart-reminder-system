"""merge heads

Revision ID: 8bd4417e95bd
Revises: 0004_add_reminder_templates, a1b2c3d4e5f6
Create Date: 2026-04-21 12:14:14.976033

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '8bd4417e95bd'
down_revision: Union[str, None] = ('0004_add_reminder_templates', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
