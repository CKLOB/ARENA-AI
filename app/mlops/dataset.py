"""시세 수집과 라벨링.

Yahoo Finance chart API 를 쓴다. 키가 필요 없고 US 주식과 COIN 을 모두 준다.
이 환경에서 Binance / Coinbase / Kraken / stooq 는 전부 연결이 막혀 있었다.
"""

import json
import logging
import ssl
import urllib.request

import certifi
import pandas as pd

from app.mlops.features import MIN_ROWS, build_features
from app.shared.enums import Market

logger = logging.getLogger(__name__)

# KR 은 브로커 계좌 대기 중이라 비활성이다.
DEFAULT_UNIVERSE: dict[Market, list[str]] = {
    Market.US: ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY"],
    Market.COIN: ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
}
DEFAULT_HORIZON = 5
DEFAULT_RANGE = "10y"

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
# urllib 은 macOS 시스템 CA 를 못 찾아 CERTIFICATE_VERIFY_FAILED 를 낸다. certifi 를 명시한다.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def fetch_ohlcv(symbol: str, range_: str = DEFAULT_RANGE) -> pd.DataFrame:
    """일봉 close / volume. 실패하면 예외를 그대로 올린다."""
    url = f"{_CHART_URL.format(symbol=symbol)}?range={range_}&interval=1d"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    # ponytail: 캐싱하지 않는다. 학습은 가끔 돌리므로 매번 받는 편이 단순하다.
    with urllib.request.urlopen(request, timeout=30, context=_SSL_CONTEXT) as response:
        payload = json.load(response)

    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    return pd.DataFrame(
        {"close": quote["close"], "volume": quote["volume"]},
        index=pd.to_datetime(result["timestamp"], unit="s"),
    ).dropna()


def build_dataset(
    universe: dict[Market, list[str]] | None = None,
    horizon: int = DEFAULT_HORIZON,
    range_: str = DEFAULT_RANGE,
) -> pd.DataFrame:
    """피처 + label + symbol + date 프레임. 종목별로 만들어 세로로 붙인다."""
    universe = universe or DEFAULT_UNIVERSE
    frames = []

    for market, symbols in universe.items():
        for symbol in symbols:
            try:
                ohlcv = fetch_ohlcv(symbol, range_)
            except Exception:
                logger.exception("%s 수집 실패 - 건너뛴다", symbol)
                continue

            if len(ohlcv) < MIN_ROWS + horizon:
                logger.warning("%s 행 부족(%d) - 건너뛴다", symbol, len(ohlcv))
                continue

            frame = build_features(ohlcv, market)
            # 라벨: horizon 일 뒤 종가가 오늘보다 높은가.
            frame["label"] = (ohlcv["close"].shift(-horizon) > ohlcv["close"]).astype("Int64")
            # 꼬리 horizon 행은 미래를 모른다. shift 가 NaN 을 남기므로 dropna 로 함께 잘린다.
            frame["label"] = frame["label"].where(ohlcv["close"].shift(-horizon).notna())
            frame["symbol"] = symbol
            frames.append(frame.dropna())
            logger.info("%s %d행", symbol, len(frames[-1]))

    if not frames:
        raise RuntimeError("수집된 데이터가 없다")

    dataset = pd.concat(frames)
    dataset["date"] = dataset.index
    return dataset.reset_index(drop=True)
