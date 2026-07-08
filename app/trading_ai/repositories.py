from sqlalchemy import select
from sqlalchemy.orm import Session

from app.trading_ai.models import DecisionLog, ShapValue


class DecisionLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, decision_log: DecisionLog) -> DecisionLog:
        self.db.add(decision_log)
        self.db.flush()
        return decision_log

    def get_by_id(self, decision_id: int) -> DecisionLog | None:
        return self.db.get(DecisionLog, decision_id)

    def list_by_challenge_id(self, challenge_id: int, limit: int = 100) -> list[DecisionLog]:
        stmt = (
            select(DecisionLog)
            .where(DecisionLog.challenge_id == challenge_id)
            .order_by(DecisionLog.decided_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))


class ShapValueRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_many(self, shap_values: list[ShapValue]) -> list[ShapValue]:
        self.db.add_all(shap_values)
        self.db.flush()
        return shap_values

    def list_by_decision_id(self, decision_id: int) -> list[ShapValue]:
        stmt = select(ShapValue).where(ShapValue.decision_id == decision_id)
        return list(self.db.scalars(stmt))
