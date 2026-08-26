from pydantic import Field

from app.shared.schemas import CamelModel

# ponytail: 이력 원소의 스키마는 박지 않는다. Spring이 필드를 바꿔도 안 깨진다.
# 대신 개수 상한을 둔다 - 프롬프트 폭발과 토큰 비용을 막는 유일한 방어선이다.
MAX_HISTORY_ITEMS = 200


class FeedbackRequest(CamelModel):
    challenge_id: int
    order_history: list[dict] = Field(max_length=MAX_HISTORY_ITEMS)
    recommendation_history: list[dict] = Field(max_length=MAX_HISTORY_ITEMS)
    final_return_rate: float


class FeedbackResponse(CamelModel):
    feedback_text: str
