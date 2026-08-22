import json
import logging
import os
from functools import lru_cache

import anthropic
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"
# max_tokens는 thinking과 응답 텍스트를 합쳐서 제한한다.
# 3~5문장이라고 작게 주면 thinking이 다 먹고 본문이 잘린다.
MAX_TOKENS = 2000
TIMEOUT_SECONDS = 30.0

SYSTEM_PROMPT = """당신은 모의투자 배틀 서비스의 학습 도우미입니다.
실제 투자가 아니라 교육이 목적이므로, 사용자가 자신의 매매 패턴을 돌아보게 돕는 것이 당신의 역할입니다.

작성 규칙:
- 한국어로 3~5문장.
- 챌린지 결과와 매매·추천 이력에서 드러난 패턴을 짚어주는 회고 톤.
- 잘한 점과 아쉬운 점을 모두 언급하되 수익률만으로 단정하지 않는다.
- 투자 조언은 하지 않는다. 특정 종목 매수·매도 권유, 목표가, 향후 전망을 쓰지 않는다.
- 사족 없이 피드백 본문만 출력한다."""


@lru_cache
def get_client() -> anthropic.Anthropic:
    # Spring이 동기로 기다린다. SDK 기본 타임아웃 10분은 너무 길다.
    return anthropic.Anthropic(timeout=TIMEOUT_SECONDS)


def generate_feedback(
    *,
    challenge_id: int,
    order_history: list[dict],
    recommendation_history: list[dict],
    final_return_rate: float,
) -> str:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ANTHROPIC_API_KEY is not configured")

    payload = {
        "challengeId": challenge_id,
        "orderHistory": order_history,
        "recommendationHistory": recommendation_history,
        "finalReturnRate": final_return_rate,
    }

    response = get_client().messages.create(
        model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        # temperature 같은 샘플링 파라미터는 Opus 5에서 400이다. 톤은 전부 프롬프트로 잡는다.
        # thinking을 끄면 <thinking> 태그가 본문에 새는 실패 모드가 있어 effort만 낮춘다.
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )

    if response.stop_reason == "refusal":
        # 거절이면 content가 비어 있다. 인덱싱하기 전에 걸러야 한다.
        logger.error("claude refused feedback generation: %s", response.stop_details)
        raise RuntimeError("feedback generation refused")

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise RuntimeError("claude returned no text")
    return text
