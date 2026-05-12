"""runtime_conversations: soft-hide from operator list

Revision ID: 0005_runtime_conversation_hidden
Revises: 0004_runtime_conversation_holder
Create Date: 2026-05-12

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_runtime_conversation_hidden"
down_revision = "0004_runtime_conversation_holder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runtime_conversations",
        sa.Column(
            "hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("runtime_conversations", "hidden")
