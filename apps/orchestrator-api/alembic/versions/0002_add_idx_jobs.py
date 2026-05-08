"""add idx jobs tables

Revision ID: 0002_add_idx_jobs
Revises: 0001_init_kb
Create Date: 2026-05-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_add_idx_jobs"
down_revision = "0001_init_kb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idx_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("total_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_documents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("indexed_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idx_jobs_status", "idx_jobs", ["status"])
    op.create_index("ix_idx_jobs_document_id", "idx_jobs", ["document_id"])

    op.create_table(
        "idx_job_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idx_job_events_job_id", "idx_job_events", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_idx_job_events_job_id", table_name="idx_job_events")
    op.drop_table("idx_job_events")

    op.drop_index("ix_idx_jobs_document_id", table_name="idx_jobs")
    op.drop_index("ix_idx_jobs_status", table_name="idx_jobs")
    op.drop_table("idx_jobs")

