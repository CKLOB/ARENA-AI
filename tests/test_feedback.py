import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.feedback.schemas import MAX_HISTORY_ITEMS
from app.main import app

API_KEY = "test-key"
URL = "/internal/ai/feedback"
BODY = {
    "challengeId": 1,
    "orderHistory": [{"symbol": "AAPL", "action": "BUY", "quantity": 10, "price": 180.5}],
    "recommendationHistory": [{"symbol": "MSFT", "accepted": False}],
    "finalReturnRate": -3.2,
}


def fake_response(text="추천을 한 번도 따르지 않으셨네요.", stop_reason="end_turn"):
    blocks = [SimpleNamespace(type="text", text=text)] if text else []
    return SimpleNamespace(stop_reason=stop_reason, stop_details=None, content=blocks)


class FeedbackEndpointTest(unittest.TestCase):
    def setUp(self):
        os.environ["INTERNAL_API_KEY"] = API_KEY
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        os.environ.pop("INTERNAL_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def post(self, body=None, headers=None):
        return self.client.post(URL, json=body or BODY, headers=headers or {"X-Internal-Api-Key": API_KEY})

    def test_missing_api_key_is_unauthorized(self):
        response = self.client.post(URL, json=BODY)
        self.assertEqual(response.status_code, 401)

    def test_valid_request_returns_feedback_text(self):
        client = MagicMock()
        client.messages.create.return_value = fake_response()
        with patch("app.feedback.generator.get_client", return_value=client):
            response = self.post()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"feedbackText": "추천을 한 번도 따르지 않으셨네요."})

        kwargs = client.messages.create.call_args.kwargs
        # Opus 5에서 400을 내는 파라미터가 섞이면 안 된다.
        self.assertNotIn("temperature", kwargs)
        self.assertEqual(kwargs["thinking"], {"type": "adaptive"})
        # thinking과 본문이 max_tokens를 나눠 쓴다. 본문이 잘리지 않을 만큼은 줘야 한다.
        self.assertGreaterEqual(kwargs["max_tokens"], 1000)
        self.assertIn("투자 조언은 하지 않는다", kwargs["system"])

    def test_missing_field_returns_422(self):
        body = {k: v for k, v in BODY.items() if k != "finalReturnRate"}
        response = self.post(body)
        self.assertEqual(response.status_code, 422)
        self.assertIn("error", response.json())

    def test_oversized_history_is_rejected(self):
        body = {**BODY, "orderHistory": [{"symbol": "AAPL"}] * (MAX_HISTORY_ITEMS + 1)}
        response = self.post(body)
        self.assertEqual(response.status_code, 422)

    def test_refusal_returns_500(self):
        client = MagicMock()
        client.messages.create.return_value = fake_response(text=None, stop_reason="refusal")
        with patch("app.feedback.generator.get_client", return_value=client):
            response = self.post()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["message"], "internal server error")

    def test_api_failure_returns_500(self):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        with patch("app.feedback.generator.get_client", return_value=client):
            response = self.post()

        self.assertEqual(response.status_code, 500)

    def test_missing_anthropic_key_returns_503(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SERVICE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
