from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.shared.enums import AiStrategy, Market, TradingAction
from app.trading_ai.models import DecisionLog
from app.trading_ai.repositories import DecisionLogRepository


def record_decision(
    db: Session,
    *,
    challenge_id: int,
    participant_id: int,
    symbol_code: str,
    market: Market,
    ai_strategy: AiStrategy,
    features: dict[str, float],
    probability: float,
    action: TradingAction,
    model_version: str,
    order_id: int | None = None,
) -> int:
    """결정 로그 한 행을 남기고 id를 돌려준다. 추천 엔드포인트도 같은 함수를 쓴다.

    SHAP 설명, 관측 대시보드, 재학습이 전부 이 행에 의존한다 (CLAUDE.md 비협상 항목).
    """
    log = DecisionLog(
        challenge_id=challenge_id,
        participant_id=participant_id,
        order_id=order_id,
        symbol_code=symbol_code,
        market=market,
        ai_strategy=ai_strategy,
        feature_snapshot=features,
        model_output_probability=Decimal(str(round(probability, 4))),
        action=action,
        model_version=model_version,
        decided_at=datetime.now(timezone.utc),
    )
    DecisionLogRepository(db).add(log)  # flush까지 하므로 여기서 id가 잡힌다
    decision_id = log.id
    db.commit()
    return decision_id
