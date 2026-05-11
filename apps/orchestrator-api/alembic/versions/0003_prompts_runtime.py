"""prompts + runtime tables

Revision ID: 0003_prompts_runtime
Revises: 0002_add_idx_jobs
Create Date: 2026-05-11

"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0003_prompts_runtime"
down_revision = "0002_add_idx_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    op.create_table(
        "prompt_templates",
        sa.Column("prompt_key", sa.String(length=64), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("prompt_key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompt_versions_prompt_key", "prompt_versions", ["prompt_key"])
    op.create_unique_constraint(
        "uq_prompt_versions_prompt_key_version", "prompt_versions", ["prompt_key", "version"]
    )

    op.create_table(
        "runtime_conversations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runtime_conversations_user", "runtime_conversations", ["user_id"])

    op.create_table(
        "runtime_messages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runtime_messages_conversation_id", "runtime_messages", ["conversation_id"])

    op.create_table(
        "runtime_agent_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runtime_agent_logs_conversation_id", "runtime_agent_logs", ["conversation_id"])

    prompt_templates = sa.table(
        "prompt_templates",
        sa.column("prompt_key", sa.String(length=64)),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        prompt_templates,
        [
            {"prompt_key": "system", "description": "Core system prompt", "created_at": now},
            {"prompt_key": "answer_policy", "description": "Answer policy", "created_at": now},
            {"prompt_key": "fallback", "description": "Fallback text", "created_at": now},
            {"prompt_key": "channel_style", "description": "Channel style", "created_at": now},
        ],
    )

    def v(pid: str, key: str, version: int, content: str) -> dict:
        return {
            "id": pid,
            "prompt_key": key,
            "version": version,
            "content": content,
            "created_at": now,
        }

    prompt_versions = sa.table(
        "prompt_versions",
        sa.column("id", sa.String(length=64)),
        sa.column("prompt_key", sa.String(length=64)),
        sa.column("version", sa.Integer()),
        sa.column("content", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        prompt_versions,
        [
            v(
                "pv_system_1",
                "system",
                1,
                "Ты — агент технической поддержки вендоров. Отвечай только по предоставленному контексту из базы знаний.",
            ),
            v(
                "pv_answer_policy_1",
                "answer_policy",
                1,
                "Если в контексте нет ответа — скажи прямо. Не выдумывай. При низкой уверенности укажи, что нужен оператор.",
            ),
            v(
                "pv_fallback_1",
                "fallback",
                1,
                "В базе знаний нет достаточной информации для точного ответа.",
            ),
            v(
                "pv_channel_style_1",
                "channel_style",
                1,
                "Отвечай кратко и по делу. Если уместно — перечисли шаги.",
            ),
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_agent_logs_conversation_id", table_name="runtime_agent_logs")
    op.drop_table("runtime_agent_logs")

    op.drop_index("ix_runtime_messages_conversation_id", table_name="runtime_messages")
    op.drop_table("runtime_messages")

    op.drop_index("ix_runtime_conversations_user", table_name="runtime_conversations")
    op.drop_table("runtime_conversations")

    op.drop_constraint("uq_prompt_versions_prompt_key_version", "prompt_versions", type_="unique")
    op.drop_index("ix_prompt_versions_prompt_key", table_name="prompt_versions")
    op.drop_table("prompt_versions")

    op.drop_table("prompt_templates")
