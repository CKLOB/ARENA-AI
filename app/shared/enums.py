from enum import Enum


class Market(str, Enum):
    KR = "KR"
    US = "US"
    COIN = "COIN"


class TradingAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class AiStrategy(str, Enum):
    STABLE = "STABLE"
    AGGRESSIVE = "AGGRESSIVE"
    TREND = "TREND"


class DecisionType(str, Enum):
    """결정 로그의 출처. 재학습 때 매매 결정과 추천을 섞으면 안 된다."""

    TRADING = "TRADING"
    RECOMMENDATION = "RECOMMENDATION"


class ModelStatus(str, Enum):
    CHAMPION = "CHAMPION"
    CHALLENGER = "CHALLENGER"
    RETIRED = "RETIRED"
