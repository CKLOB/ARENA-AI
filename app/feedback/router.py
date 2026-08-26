from fastapi import APIRouter, Depends

from app.feedback.generator import generate_feedback
from app.feedback.schemas import FeedbackRequest, FeedbackResponse
from app.shared.http import verify_internal_api_key

router = APIRouter(prefix="/internal/ai", dependencies=[Depends(verify_internal_api_key)])


@router.post("/feedback", response_model=FeedbackResponse)
def create_feedback(body: FeedbackRequest) -> FeedbackResponse:
    # 피드백은 결정이 아니라 텍스트 생성이다. decision_log를 남기지 않고 DB도 쓰지 않는다.
    text = generate_feedback(
        challenge_id=body.challenge_id,
        order_history=body.order_history,
        recommendation_history=body.recommendation_history,
        final_return_rate=body.final_return_rate,
    )
    return FeedbackResponse(feedback_text=text)
