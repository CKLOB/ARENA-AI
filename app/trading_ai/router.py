from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.observability.decision_log import record_decision
from app.shared.db import get_db
from app.shared.enums import DecisionType
from app.shared.http import verify_internal_api_key
from app.trading_ai import predictor
from app.trading_ai.schemas import TradingDecisionRequest, TradingDecisionResponse

router = APIRouter(prefix="/internal/ai", dependencies=[Depends(verify_internal_api_key)])


@router.post("/trading-decisions", response_model=TradingDecisionResponse)
def create_trading_decision(
    body: TradingDecisionRequest,
    db: Session = Depends(get_db),
) -> TradingDecisionResponse:
    probability, model_version = predictor.predict(body.features)
    action = predictor.decide_action(probability, body.market, body.ai_strategy)

    # 로깅은 이 요청의 일부다. 나중에 따로 하는 것이 아니다.
    decision_id = record_decision(
        db,
        decision_type=DecisionType.TRADING,
        challenge_id=body.challenge_id,
        participant_id=body.participant_id,
        symbol_code=body.symbol,
        market=body.market,
        ai_strategy=body.ai_strategy,
        features=body.features,
        probability=probability,
        action=action,
        model_version=model_version,
    )

    return TradingDecisionResponse(
        decision_id=decision_id,
        action=action,
        probability=probability,
        model_version=model_version,
    )
