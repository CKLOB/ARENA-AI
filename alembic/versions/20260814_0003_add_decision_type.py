"""add decision_type and relax participant/strategy on decision_logs

Revision ID: 20260814_0003
Revises: 20260810_0002
Create Date: 2026-08-14
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260814_0003"
down_revision: str | None = "20260810_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 추천은 챌린지 단위라 참가자/전략이 없다.
    op.alter_column("decision_logs", "participant_id", nullable=True)
    op.alter_column("decision_logs", "ai_strategy", nullable=True)

    # 재학습 때 매매 결정과 추천이 섞이면 학습 데이터가 오염된다.
    op.add_column(
        "decision_logs",
        sa.Column("decision_type", sa.String(length=20), nullable=False, server_default="TRADING"),
    )
    op.create_check_constraint(
        "ck_decision_logs_decision_type",
        "decision_logs",
        "decision_type IN ('TRADING', 'RECOMMENDATION')",
    )
    op.create_index("idx_decision_logs_type_decided", "decision_logs", ["decision_type", "decided_at"])


def downgrade() -> None:
    op.drop_index("idx_decision_logs_type_decided", table_name="decision_logs")
    op.drop_constraint("ck_decision_logs_decision_type", "decision_logs", type_="check")
    op.drop_column("decision_logs", "decision_type")
    # NOT NULL로 되돌리려면 빈 값을 메워야 한다. 0002가 쓴 기본값과 같은 값으로 채운다 (행은 지우지 않는다).
    op.execute("UPDATE decision_logs SET participant_id = 0 WHERE participant_id IS NULL")
    op.execute("UPDATE decision_logs SET ai_strategy = 'STABLE' WHERE ai_strategy IS NULL")
    op.alter_column("decision_logs", "ai_strategy", nullable=False)
    op.alter_column("decision_logs", "participant_id", nullable=False)
