import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.shared.db import get_db
from app.shared.enums import AiStrategy, Market, TradingAction
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
