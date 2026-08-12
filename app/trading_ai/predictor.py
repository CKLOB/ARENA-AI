import logging
import os
from pathlib import Path

from app.shared.enums import AiStrategy, Market, TradingAction

logger = logging.getLogger(__name__)

STUB_VERSION = "stub-0"

# 시장 x 전략별 (buy_above, sell_below). 사이는 HOLD.
# COIN은 변동성이 커서 US와 같은 확률에 같은 결정을 내리면 안 된다 -> HOLD 구간을 넓게 잡는다.
# ponytail: 백테스트로 튜닝해야 하는 값이라 상수로 노출해 둔다. 결과 나오면 여기만 고친다.
THRESHOLDS: dict[Market, dict[AiStrategy, tuple[float, float]]] = {
    Market.KR: {
        AiStrategy.STABLE: (0.70, 0.30),
        AiStrategy.AGGRESSIVE: (0.55, 0.45),
        AiStrategy.TREND: (0.62, 0.38),
    },
    Market.US: {
        AiStrategy.STABLE: (0.70, 0.30),
        AiStrategy.AGGRESSIVE: (0.55, 0.45),
        AiStrategy.TREND: (0.62, 0.38),
    },
    Market.COIN: {
        AiStrategy.STABLE: (0.75, 0.25),
        AiStrategy.AGGRESSIVE: (0.60, 0.40),
        AiStrategy.TREND: (0.68, 0.32),
    },
}

_booster = None
_version = STUB_VERSION


def load_model() -> None:
    """lifespan에서 한 번 호출. 모델 파일이 없으면 스텁으로 남는다."""
    global _booster, _version

    path = Path(os.getenv("MODEL_PATH", "models/trading_lgbm.txt"))
    if not path.exists():
        logger.warning("모델 파일 없음 (%s) - 스텁으로 기동한다", path)
        return

    import lightgbm as lgb  # 무거운 import라 실제로 쓸 때만 끌어온다

    _booster = lgb.Booster(model_file=str(path))
    _version = path.stem
    logger.info("모델 로드 완료: %s", _version)


def predict(features: dict[str, float]) -> tuple[float, str]:
    """(상승 확률, 모델 버전)."""
    if _booster is None:
        # ponytail: 스텁. 학습된 Booster가 생기면 load_model()이 채우고 이 분기는 안 탄다.
        return 0.5, STUB_VERSION

    import pandas as pd

    probability = float(_booster.predict(pd.DataFrame([features]))[0])
    return probability, _version


def decide_action(probability: float, market: Market, strategy: AiStrategy) -> TradingAction:
    buy_above, sell_below = THRESHOLDS[market][strategy]
    if probability >= buy_above:
        return TradingAction.BUY
    if probability <= sell_below:
        return TradingAction.SELL
    return TradingAction.HOLD
