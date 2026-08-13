import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.shared.db import get_db
from app.shared.enums import DecisionType, TradingAction

API_KEY = "test-key"
URL = "/internal/ai/recommendations"
BODY = {
    "challengeId": 1,
    "market": "US",
    "candidates": [
        {"symbolId": 10, "symbol": "AAPL", "features": {"rsi": 55.0, "volatility": 0.3}},
        {"symbolId": 11, "symbol": "MSFT", "features": {"rsi": 48.0, "volatility": 0.2}},
    ],
}


class RecommendationEndpointTest(unittest.TestCase):
    def setUp(self):
        os.environ["INTERNAL_API_KEY"] = API_KEY
        app.dependency_overrides[get_db] = lambda: None
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        os.environ.pop("INTERNAL_API_KEY", None)

    def test_missing_api_key_is_unauthorized(self):
        response = self.client.post(URL, json=BODY)
        self.assertEqual(response.status_code, 401)

    def test_valid_request_returns_camel_case_body(self):
        with patch("app.recommendation.router.record_decision", return_value=55) as record:
            response = self.client.post(URL, json=BODY, headers={"X-Internal-Api-Key": API_KEY})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(sorted(payload), ["decisionId", "probability", "reasonText", "symbolId"])
        self.assertEqual(payload["decisionId"], 55)
        # 스텁 모델은 모든 후보가 같은 확률이라 첫 번째가 뽑힌다.
        self.assertEqual(payload["symbolId"], 10)
        self.assertIn("AAPL", payload["reasonText"])

        kwargs = record.call_args.kwargs
        self.assertEqual(kwargs["decision_type"], DecisionType.RECOMMENDATION)
        self.assertEqual(kwargs["symbol_code"], "AAPL")
        self.assertEqual(kwargs["action"], TradingAction.BUY)
        # 추천은 챌린지 단위라 참가자와 전략이 없다.
        self.assertIsNone(kwargs.get("participant_id"))
        self.assertIsNone(kwargs.get("ai_strategy"))

    def test_highest_probability_candidate_wins(self):
        # AAPL 0.4, MSFT 0.8 -> MSFT가 뽑혀야 한다.
        probabilities = {55.0: 0.4, 48.0: 0.8}

        def fake_predict(features):
            return probabilities[features["rsi"]], "fake-1"

        with patch("app.trading_ai.predictor.predict", side_effect=fake_predict):
            with patch("app.recommendation.router.record_decision", return_value=1) as record:
                response = self.client.post(URL, json=BODY, headers={"X-Internal-Api-Key": API_KEY})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["symbolId"], 11)
        self.assertEqual(response.json()["probability"], 0.8)
        self.assertEqual(record.call_args.kwargs["symbol_code"], "MSFT")

    def test_empty_candidates_is_rejected(self):
        body = {**BODY, "candidates": []}
        response = self.client.post(URL, json=body, headers={"X-Internal-Api-Key": API_KEY})
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())

    def test_inference_failure_returns_500(self):
        with patch("app.trading_ai.predictor.predict", side_effect=RuntimeError("boom")):
            response = self.client.post(URL, json=BODY, headers={"X-Internal-Api-Key": API_KEY})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["message"], "internal server error")


if __name__ == "__main__":
    unittest.main()
