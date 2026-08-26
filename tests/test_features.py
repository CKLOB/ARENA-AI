import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from app.mlops.dataset import build_dataset
from app.mlops.features import FEATURE_NAMES, build_features, market_code, rsi
from app.shared.enums import Market


def ohlcv(closes, volumes=None):
    index = pd.date_range("2024-01-01", periods=len(closes))
    volumes = volumes if volumes is not None else [1_000_000] * len(closes)
    return pd.DataFrame({"close": closes, "volume": volumes}, index=index)


class RsiTest(unittest.TestCase):
    def test_monotonic_rise_is_one(self):
        self.assertAlmostEqual(rsi(pd.Series(np.arange(100, 140, dtype=float))).iloc[-1], 1.0)

    def test_monotonic_fall_is_zero(self):
        self.assertAlmostEqual(rsi(pd.Series(np.arange(140, 100, -1, dtype=float))).iloc[-1], 0.0)

    def test_stays_normalized(self):
        rng = np.random.default_rng(0)
        values = rsi(pd.Series(100 + rng.normal(size=300).cumsum()))
        self.assertTrue(((values >= 0) & (values <= 1)).all())


class BuildFeaturesTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.closes = 100 + rng.normal(size=200).cumsum()

    def test_columns_match_feature_names_exactly(self):
        frame = build_features(ohlcv(self.closes), Market.US)
        self.assertEqual(list(frame.columns), FEATURE_NAMES)

    def test_no_nan_after_warmup(self):
        frame = build_features(ohlcv(self.closes), Market.US).dropna()
        self.assertFalse(frame.isna().any().any())
        self.assertGreater(len(frame), 150)

    def test_price_scale_does_not_change_ratios(self):
        # 가격이 100배여도 비율 피처는 같아야 한다. 이게 단일 모델로 US와 COIN을
        # 함께 학습할 수 있는 근거다.
        small = build_features(ohlcv(self.closes), Market.US).dropna()
        large = build_features(ohlcv(self.closes * 100), Market.US).dropna()
        for column in ("ma5", "ma20", "macd", "volatility", "rsi"):
            np.testing.assert_allclose(small[column], large[column], rtol=1e-9)

    def test_ratio_features_are_near_one(self):
        frame = build_features(ohlcv(self.closes), Market.US).dropna()
        for column in ("ma5", "ma20"):
            self.assertTrue((frame[column].between(0.5, 1.5)).all(), f"{column} 범위 이탈")

    def test_market_is_encoded(self):
        for market, expected in ((Market.KR, 0), (Market.US, 1), (Market.COIN, 2)):
            self.assertEqual(market_code(market), expected)
            frame = build_features(ohlcv(self.closes), market)
            self.assertTrue((frame["market"] == expected).all())


class LabelLeakageTest(unittest.TestCase):
    """라벨 꼬리 누수 방어. build_dataset이 미래를 모르는 행을 남기면 안 된다."""

    HORIZON = 5

    def test_naive_comparison_silently_hides_missing_future(self):
        # NaN 비교는 False가 되므로 shift() > close 만 쓰면 꼬리가 0으로 학습된다.
        # dataset.py가 .where()로 이걸 막는 이유다.
        close = pd.Series(np.arange(100, 130, dtype=float))
        self.assertEqual((close.shift(-self.HORIZON) > close).isna().sum(), 0)

    def test_build_dataset_drops_unlabelable_tail(self):
        rng = np.random.default_rng(2)
        rows = 200
        frame = ohlcv(100 + rng.normal(size=rows).cumsum())

        with patch("app.mlops.dataset.fetch_ohlcv", return_value=frame):
            dataset = build_dataset({Market.US: ["FAKE"]}, horizon=self.HORIZON)

        # 마지막 horizon일은 라벨을 만들 수 없으므로 데이터셋에 없어야 한다.
        self.assertLessEqual(dataset["date"].max(), frame.index[-1 - self.HORIZON])
        self.assertFalse(dataset["label"].isna().any())

    def test_label_matches_future_close(self):
        # 단조 상승이면 라벨은 전부 1이어야 한다.
        frame = ohlcv(np.arange(100, 300, dtype=float))
        with patch("app.mlops.dataset.fetch_ohlcv", return_value=frame):
            dataset = build_dataset({Market.US: ["FAKE"]}, horizon=self.HORIZON)
        self.assertEqual(dataset["label"].astype(int).sum(), len(dataset))


if __name__ == "__main__":
    unittest.main()
