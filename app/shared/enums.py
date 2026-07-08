from enum import Enum


class Market(str, Enum):
    KR = "KR"
    US = "US"
    COIN = "COIN"


class TradingAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ModelStatus(str, Enum):
    CHAMPION = "CHAMPION"
    CHALLENGER = "CHALLENGER"
    RETIRED = "RETIRED"
