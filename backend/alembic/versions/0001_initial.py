"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-20
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "SHR_V1"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),     autoincrement=True, nullable=False),
        sa.Column("username",        sa.String(50),    nullable=False),
        sa.Column("email",           sa.String(100),   nullable=False),
        sa.Column("hashed_password", sa.Text(),        nullable=False),
        sa.Column("created_at",      sa.DateTime(),    nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_users_id"),       "users", ["id"],       unique=False, schema=SCHEMA)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True,  schema=SCHEMA)
    op.create_index(op.f("ix_users_email"),    "users", ["email"],    unique=True,  schema=SCHEMA)

    op.create_table(
        "reminders",
        sa.Column("id",                  sa.Integer(),   autoincrement=True, nullable=False),
        sa.Column("user_id",             sa.Integer(),   nullable=False),
        sa.Column("title",               sa.String(200), nullable=False),
        sa.Column("phone_number",        sa.String(20),  nullable=False),
        sa.Column("scheduled_time",      sa.DateTime(),  nullable=False),
        sa.Column("audio_filename",      sa.Text(),      nullable=False),
        sa.Column("status",              sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("recurrence",          sa.String(20),  nullable=True),
        sa.Column("recurrence_end_date", sa.DateTime(),  nullable=True),
        sa.Column("call_sid",            sa.String(50),  nullable=True),
        sa.Column("retry_count",         sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("retry_gap_minutes",   sa.Integer(),   nullable=False, server_default="10"),
        sa.Column("attempt_number",      sa.Integer(),   nullable=False, server_default="1"),
        sa.Column("parent_reminder_id",  sa.Integer(),   nullable=True),
        sa.Column("created_at",          sa.DateTime(),  nullable=True),
        sa.Column("updated_at",          sa.DateTime(),  nullable=True),
        sa.ForeignKeyConstraint(["user_id"],            [f"{SCHEMA}.users.id"],     ),
        sa.ForeignKeyConstraint(["parent_reminder_id"], [f"{SCHEMA}.reminders.id"], ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(op.f("ix_reminders_id"),       "reminders", ["id"],                        unique=False, schema=SCHEMA)
    op.create_index("ix_reminders_user_id",         "reminders", ["user_id"],                   unique=False, schema=SCHEMA)
    op.create_index("ix_reminders_status_scheduled","reminders", ["status", "scheduled_time"],  unique=False, schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_reminders_status_scheduled", table_name="reminders", schema=SCHEMA)
    op.drop_index("ix_reminders_user_id",           table_name="reminders", schema=SCHEMA)
    op.drop_index(op.f("ix_reminders_id"),          table_name="reminders", schema=SCHEMA)
    op.drop_table("reminders", schema=SCHEMA)

    op.drop_index(op.f("ix_users_email"),    table_name="users", schema=SCHEMA)
    op.drop_index(op.f("ix_users_username"), table_name="users", schema=SCHEMA)
    op.drop_index(op.f("ix_users_id"),       table_name="users", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)

    op.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}"')
