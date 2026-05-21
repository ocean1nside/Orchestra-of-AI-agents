"""runtime_user_facts: remembered user attributes per channel+user_id

Revision ID: 0006_runtime_user_facts
Revises: 0005_runtime_conversation_hidden
Create Date: 2026-05-21

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_runtime_user_facts"
down_revision = "0005_runtime_conversation_hidden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_user_facts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=256), nullable=False),
        sa.Column("fact_key", sa.String(length=64), nullable=False),
        sa.Column("fact_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="extracted"),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_runtime_user_facts_channel_user",
        "runtime_user_facts",
        ["channel", "user_id"],
    )
    op.create_unique_constraint(
        "uq_runtime_user_facts_channel_user_key",
        "runtime_user_facts",
        ["channel", "user_id", "fact_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_runtime_user_facts_channel_user_key", "runtime_user_facts", type_="unique")
    op.drop_index("ix_runtime_user_facts_channel_user", table_name="runtime_user_facts")
    op.drop_table("runtime_user_facts")
