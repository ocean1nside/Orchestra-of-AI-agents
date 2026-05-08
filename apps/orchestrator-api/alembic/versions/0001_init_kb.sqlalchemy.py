"""init kb tables

Revision ID: 0001_init_kb
Revises: 
Create Date: 2026-05-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_init_kb"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_documents_status", "kb_documents", ["status"])

    op.create_table(
        "kb_document_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="knowledge_document"),
        sa.Column("original_path", sa.String(length=1024), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_document_versions_document_id", "kb_document_versions", ["document_id"])

    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kb_chunks_document_id", "kb_chunks", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_kb_chunks_document_id", table_name="kb_chunks")
    op.drop_table("kb_chunks")

    op.drop_index("ix_kb_document_versions_document_id", table_name="kb_document_versions")
    op.drop_table("kb_document_versions")

    op.drop_index("ix_kb_documents_status", table_name="kb_documents")
    op.drop_table("kb_documents")

