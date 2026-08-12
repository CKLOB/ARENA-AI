from app.shared.enums import AiStrategy, Market, TradingAction
from app.shared.schemas import CamelModel


class TradingDecisionRequest(CamelModel):
    challenge_id: int
    participant_id: int
    symbol: str
    market: Market
    ai_strategy: AiStrategy
    # ponytail: 개별 피처 키는 검증하지 않는다. 모델 피처 목록이 확정되면 여기에 박는다.
    features: dict[str, float]


class TradingDecisionResponse(CamelModel):
    decision_id: int
    action: TradingAction
    probability: float
    model_version: str
