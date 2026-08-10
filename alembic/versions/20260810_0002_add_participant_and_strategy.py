"""add participant_id and ai_strategy to decision_logs

Revision ID: 20260810_0002
Revises: 20260708_0001
Create Date: 2026-08-10
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260810_0002"
down_revision: str | None = "20260708_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0001과 같은 방식: native enum 대신 String + CHECK.
    op.add_column(
        "decision_logs",
        sa.Column("participant_id", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "decision_logs",
        sa.Column("ai_strategy", sa.String(length=10), nullable=False, server_default="STABLE"),
    )
    op.create_check_constraint(
        "ck_decision_logs_ai_strategy",
        "decision_logs",
        "ai_strategy IN ('STABLE', 'AGGRESSIVE', 'TREND')",
    )
    op.create_index("idx_decision_logs_participant_decided", "decision_logs", ["participant_id", "decided_at"])


def downgrade() -> None:
    op.drop_index("idx_decision_logs_participant_decided", table_name="decision_logs")
    op.drop_constraint("ck_decision_logs_ai_strategy", "decision_logs", type_="check")
    op.drop_column("decision_logs", "ai_strategy")
    op.drop_column("decision_logs", "participant_id")
