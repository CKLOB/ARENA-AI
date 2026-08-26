import logging
import os
from pathlib import Path

from app.mlops.features import market_code
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


def predict(features: dict[str, float], market: Market) -> tuple[float, str]:
    """(상승 확률, 모델 버전).

    LightGBM Booster는 피처 이름이 아니라 **열 순서**로 매칭한다. DataFrame으로
    넘겨도 이름을 보지 않아서, dict 키 순서가 학습 때와 다르면 에러 없이 다른
    값이 나오고 이름 오타는 조용히 통과한다. 그래서 booster가 기대하는 순서로
    직접 재배열하고 누락을 명시적으로 잡는다.
    """
    if _booster is None:
        # ponytail: 스텁. 학습된 Booster가 생기면 load_model()이 채우고 이 분기는 안 탄다.
        return 0.5, STUB_VERSION

    import pandas as pd

    # market은 요청 본문의 별도 필드로 오므로 여기서 피처에 합친다.
    values = {**features, "market": market_code(market)}
    expected = _booster.feature_name()

    missing = [name for name in expected if name not in values]
    if missing:
        raise ValueError(f"피처 누락: {missing} (기대: {expected})")

    row = pd.DataFrame([[values[name] for name in expected]], columns=expected)
    probability = float(_booster.predict(row)[0])
    return probability, _version


def decide_action(probability: float, market: Market, strategy: AiStrategy) -> TradingAction:
    buy_above, sell_below = THRESHOLDS[market][strategy]
    if probability >= buy_above:
        return TradingAction.BUY
    if probability <= sell_below:
        return TradingAction.SELL
    return TradingAction.HOLD
