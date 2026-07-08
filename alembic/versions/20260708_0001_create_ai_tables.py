"""create ai tables

Revision ID: 20260708_0001
Revises:
Create Date: 2026-07-08
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260708_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("challenge_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol_code", sa.String(length=20), nullable=False),
        sa.Column("market", sa.String(length=10), nullable=False),
        sa.Column("feature_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_output_probability", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('BUY', 'SELL', 'HOLD')", name="ck_decision_logs_action"),
        sa.CheckConstraint("market IN ('KR', 'US', 'COIN')", name="ck_decision_logs_market"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_decision_logs_challenge_decided", "decision_logs", ["challenge_id", "decided_at"])
    op.create_index("idx_decision_logs_model_version", "decision_logs", ["model_version"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("version_tag", sa.String(length=50), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("performance_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="CHALLENGER", nullable=False),
        sa.CheckConstraint("status IN ('CHAMPION', 'CHALLENGER', 'RETIRED')", name="ck_model_versions_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_tag", name="uq_model_versions_version_tag"),
    )
    op.create_index(
        "uq_model_versions_champion",
        "model_versions",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'CHAMPION'"),
    )
    op.create_table(
        "shap_values",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("decision_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_name", sa.String(length=50), nullable=False),
        sa.Column("contribution", sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column("base_value", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decision_logs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_shap_values_decision_id", "shap_values", ["decision_id"])


def downgrade() -> None:
    op.drop_index("idx_shap_values_decision_id", table_name="shap_values")
    op.drop_table("shap_values")
    op.drop_index("uq_model_versions_champion", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index("idx_decision_logs_model_version", table_name="decision_logs")
    op.drop_index("idx_decision_logs_challenge_decided", table_name="decision_logs")
    op.drop_table("decision_logs")
