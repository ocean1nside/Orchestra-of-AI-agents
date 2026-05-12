"""runtime_conversations: who replies (ai vs human/manager)

Revision ID: 0004_runtime_conversation_holder
Revises: 0003_prompts_runtime
Create Date: 2026-05-11

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_runtime_conversation_holder"
down_revision = "0003_prompts_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runtime_conversations",
        sa.Column(
            "conversation_holder",
            sa.String(length=16),
            nullable=False,
            server_default="ai",
        ),
    )


def downgrade() -> None:
    op.drop_column("runtime_conversations", "conversation_holder")
