"""피처 계산. Spring Boot 와 맞춰야 하는 계약의 원본이다.

Spring 이 `/internal/ai/trading-decisions` 로 보내는 features 는 여기 정의와
같은 공식으로 계산되어야 한다. 이름과 개수가 맞아도 정의가 다르면 모델은
에러 없이 틀린 예측을 낸다.

ma5 / ma20 / macd 가 종가로 나눈 **비율**이라는 점이 핵심이다. 절대값을 쓰면
AAPL(300 규모)과 BTC(70000 규모)이 같은 피처 공간에 들어가지 않는다.
"""

import numpy as np
import pandas as pd

from app.shared.enums import Market

RSI_PERIOD = 14
MA_SHORT = 5
MA_LONG = 20
MACD_FAST = 12
MACD_SLOW = 26
VOL_WINDOW = 20

# 학습과 추론이 공유하는 정순서. LightGBM Booster 는 이름이 아니라 열 순서로
# 매칭하므로 이 순서가 계약이다.
FEATURE_NAMES = ["rsi", "ma5", "ma20", "volumeChange", "macd", "volatility", "market"]

CATEGORICAL_FEATURES = ["market"]

# 피처 생성에 필요한 최소 행 수. EMA26 이 가장 길다.
MIN_ROWS = MACD_SLOW + VOL_WINDOW


def market_code(market: Market) -> int:
    return {Market.KR: 0, Market.US: 1, Market.COIN: 2}[market]


def rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """0~1 로 정규화한 RSI. 통상 0~100 인 값을 100 으로 나눈다."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    # loss 가 0이면(하락이 없으면) RSI 는 1.0 이다. 0으로 나누기를 NaN 으로 두고 채운다.
    rs = gain / loss.replace(0, np.nan)
    return (1 - 1 / (1 + rs)).fillna(1.0)


def build_features(df: pd.DataFrame, market: Market) -> pd.DataFrame:
    """OHLCV -> FEATURE_NAMES 순서의 피처 프레임.

    df 는 close, volume 열과 DatetimeIndex 를 가져야 한다.
    선행 구간(이동평균이 정의되지 않는 앞부분)은 호출자가 dropna 로 잘라낸다.
    """
    close, volume = df["close"], df["volume"]

    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    returns = close.pct_change()

    out = pd.DataFrame(
        {
            "rsi": rsi(close),
            "ma5": close.rolling(MA_SHORT).mean() / close,
            "ma20": close.rolling(MA_LONG).mean() / close,
            "volumeChange": volume / volume.rolling(VOL_WINDOW).mean() - 1,
            "macd": (ema_fast - ema_slow) / close,
            "volatility": returns.rolling(VOL_WINDOW).std(),
            "market": market_code(market),
        },
        index=df.index,
    )
    return out[FEATURE_NAMES]
