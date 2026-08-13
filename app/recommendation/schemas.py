from pydantic import Field

from app.shared.enums import Market
from app.shared.schemas import CamelModel


class Candidate(CamelModel):
    # symbolId는 Spring symbol 테이블 PK를 ID로만 참조한다 (크로스 DB, FK 없음).
    symbol_id: int
    symbol: str
    features: dict[str, float]


class RecommendationRequest(CamelModel):
    challenge_id: int
    market: Market
    candidates: list[Candidate] = Field(min_length=1)


class RecommendationResponse(CamelModel):
    symbol_id: int
    reason_text: str
    probability: float
    decision_id: int
