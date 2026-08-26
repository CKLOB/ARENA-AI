import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.shared.db import get_db
from app.shared.enums import AiStrategy, DecisionType, Market, TradingAction
from app.mlops.features import FEATURE_NAMES
from app.trading_ai import predictor
from app.trading_ai.predictor import decide_action

API_KEY = "test-key"
URL = "/internal/ai/trading-decisions"
BODY = {
    "challengeId": 1,
    "participantId": 7,
    "symbol": "AAPL",
    "market": "US",
    "aiStrategy": "STABLE",
    "features": {"rsi": 55.0, "ma5": 1.0, "ma20": 1.0, "volumeChange": 0.1, "macd": 0.2, "volatility": 0.3},
}


class TradingDecisionEndpointTest(unittest.TestCase):
    def setUp(self):
        os.environ["INTERNAL_API_KEY"] = API_KEY
        # 실 DB를 띄우지 않는다. 로깅 호출 여부만 확인한다.
        app.dependency_overrides[get_db] = lambda: None
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        os.environ.pop("INTERNAL_API_KEY", None)

    def test_missing_api_key_is_unauthorized(self):
        response = self.client.post(URL, json=BODY)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_wrong_api_key_is_unauthorized(self):
        response = self.client.post(URL, json=BODY, headers={"X-Internal-Api-Key": "nope"})
        self.assertEqual(response.status_code, 401)

    def test_valid_request_returns_camel_case_body(self):
        with patch("app.trading_ai.router.record_decision", return_value=123) as record:
            response = self.client.post(URL, json=BODY, headers={"X-Internal-Api-Key": API_KEY})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"decisionId": 123, "action": "HOLD", "probability": 0.5, "modelVersion": "stub-0"},
        )
        # 결정 로깅은 엔드포인트의 일부다 (CLAUDE.md 비협상 항목).
        record.assert_called_once()
        kwargs = record.call_args.kwargs
        self.assertEqual(kwargs["decision_type"], DecisionType.TRADING)
        self.assertEqual(kwargs["challenge_id"], 1)
        self.assertEqual(kwargs["participant_id"], 7)
        self.assertEqual(kwargs["ai_strategy"], AiStrategy.STABLE)
        self.assertEqual(kwargs["features"], BODY["features"])

    def test_invalid_body_returns_formatted_422(self):
        response = self.client.post(URL, json={"challengeId": 1}, headers={"X-Internal-Api-Key": API_KEY})
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())

    def test_inference_failure_returns_500(self):
        with patch("app.trading_ai.predictor.predict", side_effect=RuntimeError("boom")):
            response = self.client.post(URL, json=BODY, headers={"X-Internal-Api-Key": API_KEY})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["message"], "internal server error")


class FeatureOrderingTest(unittest.TestCase):
    """LightGBM Booster는 피처 이름이 아니라 열 순서로 매칭한다.

    predictor가 booster.feature_name() 순서로 재배열하지 않으면, Spring이 보내는
    JSON 필드 순서가 학습 때와 다를 때 에러 없이 다른 확률이 나온다. 스텁은 항상
    0.5라 이 버그가 드러나지 않으므로 가짜 booster로 실제 동작을 검증한다.
    """

    FEATURES = {
        "rsi": 0.55,
        "ma5": 1.01,
        "ma20": 0.99,
        "volumeChange": 0.1,
        "macd": 0.002,
        "volatility": 0.015,
    }

    def setUp(self):
        # 열 순서에 의존하는 booster를 흉내내: 받은 순서 그대로 가중합한다.
        self.booster = MagicMock()
        self.booster.feature_name.return_value = FEATURE_NAMES
        self.booster.predict.side_effect = lambda frame: [
            float(sum((i + 1) * v for i, v in enumerate(frame.iloc[0])))
        ]

    def test_key_order_does_not_change_prediction(self):
        with patch.object(predictor, "_booster", self.booster):
            straight, _ = predictor.predict(self.FEATURES, Market.US)
            reversed_, _ = predictor.predict(
                {k: self.FEATURES[k] for k in reversed(list(self.FEATURES))}, Market.US
            )
        self.assertEqual(straight, reversed_)

    def test_columns_are_reordered_to_booster_order(self):
        with patch.object(predictor, "_booster", self.booster):
            predictor.predict({k: self.FEATURES[k] for k in reversed(list(self.FEATURES))}, Market.US)
        frame = self.booster.predict.call_args.args[0]
        self.assertEqual(list(frame.columns), FEATURE_NAMES)

    def test_missing_feature_raises(self):
        broken = {k: v for k, v in self.FEATURES.items() if k != "macd"}
        with patch.object(predictor, "_booster", self.booster):
            with self.assertRaises(ValueError):
                predictor.predict(broken, Market.US)

    def test_misspelled_feature_raises(self):
        # 이름만 틀리고 개수가 맞으면 LightGBM은 조용히 통과시킨다. 여기서 잡아야 한다.
        typo = {("volume_change" if k == "volumeChange" else k): v for k, v in self.FEATURES.items()}
        with patch.object(predictor, "_booster", self.booster):
            with self.assertRaises(ValueError):
                predictor.predict(typo, Market.US)

    def test_market_reaches_the_model(self):
        with patch.object(predictor, "_booster", self.booster):
            us, _ = predictor.predict(self.FEATURES, Market.US)
            coin, _ = predictor.predict(self.FEATURES, Market.COIN)
        self.assertNotEqual(us, coin)


class DecideActionTest(unittest.TestCase):
    def test_thresholds_are_separated_per_market(self):
        # COIN은 변동성이 커서 US와 같은 확률에 같은 결정이 나오면 안 된다.
        self.assertEqual(decide_action(0.72, Market.US, AiStrategy.STABLE), TradingAction.BUY)
        self.assertEqual(decide_action(0.72, Market.COIN, AiStrategy.STABLE), TradingAction.HOLD)

    def test_stub_probability_is_hold_everywhere(self):
        for market in Market:
            for strategy in AiStrategy:
                self.assertEqual(decide_action(0.5, market, strategy), TradingAction.HOLD)


if __name__ == "__main__":
    unittest.main()
