import json
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.routers import chat
from main import app
from monitor import ApiMonitorMiddleware

USER = {"role": "user", "content": "Remember the color indigo."}
ASSISTANT = {"role": "assistant", "content": "I'll remember indigo."}
FOLLOW_UP = {"role": "user", "content": "Which color?"}
FIXTURE_TOKEN = "fixture-token"


def provider_reply(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def provider_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.client = self.enterContext(TestClient(app))
        self.enterContext(patch.dict(os.environ, {"OPENAI_API_KEY": FIXTURE_TOKEN}))

    def test_forwards_ordered_history_without_monitor_logging(self):
        def provider(request):
            self.assertEqual(str(request.url), "https://api.openai.com/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], f"Bearer {FIXTURE_TOKEN}")
            data = json.loads(request.content)
            self.assertEqual(data["messages"], [USER, ASSISTANT, FOLLOW_UP])
            self.assertEqual(data["model"], "gpt-4o-mini")
            self.assertFalse(data["store"])
            return provider_reply("Indigo.")

        with (
            patch.object(chat, "openai_client", side_effect=lambda: provider_client(provider)),
            patch.object(ApiMonitorMiddleware, "_send") as monitor,
        ):
            response = self.client.post("/api/chat", json={"messages": [USER, ASSISTANT, FOLLOW_UP]})
        monitor.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": "Indigo."})
        self.assertNotIn(FIXTURE_TOKEN, response.text)

    def test_invalid_history_never_reaches_provider(self):
        cases = [
            [],
            [ASSISTANT],
            [USER, ASSISTANT],
            [USER, USER, FOLLOW_UP],
            [{"role": "system", "content": "Instructions"}],
            [{"role": "user", "content": "  "}],
            [{"role": "user", "content": "x" * 8001}],
            [USER, ASSISTANT] * 11 + [FOLLOW_UP],
        ]
        with patch.object(chat, "openai_client") as provider:
            for messages in cases:
                with self.subTest(roles=[message["role"] for message in messages]):
                    response = self.client.post("/api/chat", json={"messages": messages})
                    self.assertEqual(response.status_code, 422)
            provider.assert_not_called()

    def test_missing_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), patch.object(chat, "openai_client") as provider:
            response = self.client.post("/api/chat", json={"messages": [USER]})
        provider.assert_not_called()
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENAI_API_KEY", response.json()["detail"])

    def test_provider_failures_return_safe_errors(self):
        for upstream, expected in [
            (httpx.Response(401, text=FIXTURE_TOKEN), 502),
            (httpx.Response(429, text=FIXTURE_TOKEN), 429),
            (httpx.Response(200, text="invalid JSON"), 502),
            (provider_reply("   "), 502),
        ]:
            with self.subTest(status=upstream.status_code):
                with patch.object(chat, "openai_client", side_effect=lambda: provider_client(lambda _: upstream)):
                    response = self.client.post("/api/chat", json={"messages": [USER]})
                self.assertEqual(response.status_code, expected)
                self.assertNotIn(FIXTURE_TOKEN, response.text)

    def test_provider_timeout(self):
        def provider(request):
            raise httpx.ReadTimeout("fixture timeout", request=request)

        with patch.object(chat, "openai_client", side_effect=lambda: provider_client(provider)):
            response = self.client.post("/api/chat", json={"messages": [USER]})
        self.assertEqual(response.status_code, 504)
        self.assertIn("Try again", response.json()["detail"])
