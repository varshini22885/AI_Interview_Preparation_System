"""add resume processing status

Revision ID: a8b7c6d5e4f3
Revises: 7f1c2a9d4e10
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a8b7c6d5e4f3"
down_revision: str | None = "7f1c2a9d4e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("status", sa.String(length=32), server_default="UPLOADED", nullable=False))
    op.create_index("ix_resumes_status", "resumes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_resumes_status", table_name="resumes")
    op.drop_column("resumes", "status")
