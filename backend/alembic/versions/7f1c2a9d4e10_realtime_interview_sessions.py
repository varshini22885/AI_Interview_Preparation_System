"""realtime interview sessions

Revision ID: 7f1c2a9d4e10
Revises: ed695e15ff26
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "7f1c2a9d4e10"
down_revision: str | None = "ed695e15ff26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "realtime_interview_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("disconnect_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", "user_id", "status", name="uq_realtime_session_active"),
    )
    op.create_index("ix_realtime_sessions_user", "realtime_interview_sessions", ["user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_realtime_sessions_user", table_name="realtime_interview_sessions")
    op.drop_table("realtime_interview_sessions")
