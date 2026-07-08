from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import Base
from app.shared.enums import Market, TradingAction


class DecisionLog(Base):
    __tablename__ = "decision_logs"
    __table_args__ = (
        CheckConstraint("market IN ('KR', 'US', 'COIN')", name="ck_decision_logs_market"),
        CheckConstraint("action IN ('BUY', 'SELL', 'HOLD')", name="ck_decision_logs_action"),
        Index("idx_decision_logs_challenge_id", "challenge_id"),
        Index("idx_decision_logs_decided_at", "decided_at"),
        Index("idx_decision_logs_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    symbol_code: Mapped[str] = mapped_column(String(20), nullable=False)
    market: Mapped[Market] = mapped_column(String(10), nullable=False)
    feature_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_output_probability: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    action: Mapped[TradingAction] = mapped_column(String(10), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    shap_values: Mapped[list["ShapValue"]] = relationship(back_populates="decision")


class ShapValue(Base):
    __tablename__ = "shap_values"
    __table_args__ = (Index("idx_shap_values_decision_id", "decision_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("decision_logs.id"), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(50), nullable=False)
    contribution: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False)
    base_value: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)

    decision: Mapped[DecisionLog] = relationship(back_populates="shap_values")
