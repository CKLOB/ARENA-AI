from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.observability.decision_log import record_decision
from app.recommendation.schemas import RecommendationRequest, RecommendationResponse
from app.shared.db import get_db
from app.shared.enums import DecisionType, Market, TradingAction
from app.shared.http import verify_internal_api_key
from app.trading_ai import predictor

router = APIRouter(prefix="/internal/ai", dependencies=[Depends(verify_internal_api_key)])


def build_reason_text(symbol: str, market: Market, probability: float) -> str:
    # ponytail: SHAP가 붙으면 상위 기여 피처를 문장에 넣는다. 지금은 확률만 쓴다.
    return f"{market.value} 시장 {symbol}의 상승 확률이 {probability:.0%}로 후보 중 가장 높습니다."


@router.post("/recommendations", response_model=RecommendationResponse)
def create_recommendation(
    body: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    scored = [(predictor.predict(candidate.features, body.market), candidate) for candidate in body.candidates]
    # 스텁 모델은 모든 후보가 같은 확률이라 첫 번째가 뽑힌다. max는 동점에서 앞선 것을 유지한다.
    (probability, model_version), best = max(scored, key=lambda item: item[0][0])

    decision_id = record_decision(
        db,
        decision_type=DecisionType.RECOMMENDATION,
        challenge_id=body.challenge_id,
        symbol_code=best.symbol,
        market=body.market,
        features=best.features,
        probability=probability,
        # 추천 카드는 매수 후보 제시다. 전략이 없어 decide_action의 임계값은 쓸 수 없다.
        action=TradingAction.BUY,
        model_version=model_version,
    )

    return RecommendationResponse(
        symbol_id=best.symbol_id,
        reason_text=build_reason_text(best.symbol, body.market, probability),
        probability=probability,
        decision_id=decision_id,
    )
