import asyncio
import json
import os
import socket
import threading
import time
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import uvicorn
from playwright.sync_api import expect, sync_playwright

from app.routers import chat
from main import app
from monitor import ApiMonitorMiddleware
from test_chat import ASSISTANT, FIXTURE_TOKEN, FOLLOW_UP, USER, provider_client, provider_reply


class ChatBrowserTests(unittest.TestCase):
    def test_chat_loading_multiturn_error_retry_and_reset(self):
        requests = []
        first_request_can_finish = threading.Event()

        async def provider(request):
            messages = json.loads(request.content)["messages"]
            requests.append(messages)
            if len(requests) == 1:
                await asyncio.to_thread(first_request_can_finish.wait, 10)
                return provider_reply(ASSISTANT["content"])
            if len(requests) == 2:
                return httpx.Response(500, json={"error": "internal provider detail"})
            return provider_reply("Indigo. <b>Plain text</b>")

        self.enterContext(patch.dict(os.environ, {"OPENAI_API_KEY": FIXTURE_TOKEN}))
        self.enterContext(patch.object(chat, "openai_client", side_effect=lambda: provider_client(provider)))
        self.enterContext(patch.object(ApiMonitorMiddleware, "_send", new_callable=AsyncMock))
        listener = self.enterContext(socket.socket())
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="off"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()

        def stop_server():
            first_request_can_finish.set()
            server.should_exit = True
            thread.join(10)
            self.assertFalse(thread.is_alive())

        self.addCleanup(stop_server)
        base_url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        for _ in range(200):
            if server.started:
                break
            time.sleep(0.025)
        self.assertTrue(server.started)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.environ.get("CHAT_TEST_CHROMIUM"))
            try:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page_errors = []
                browser_chat_requests = []
                page.on("pageerror", lambda error: page_errors.append(error))
                page.on(
                    "request",
                    lambda request: browser_chat_requests.append(request)
                    if request.url == f"{base_url}/api/chat" else None,
                )
                page.goto(base_url)
                page.get_by_role("button", name="Chat", exact=True).click()
                message = page.get_by_role("textbox", name="Message")
                send = page.get_by_role("button", name="Send")
                reset = page.get_by_role("button", name="New chat")
                log = page.get_by_role("log")
                expect(send).to_be_disabled()

                message.fill(USER["content"])
                send.click()
                expect(page.get_by_role("status")).to_have_text("Waiting for a reply…")
                expect(send).to_be_disabled()
                expect(reset).to_be_disabled()
                expect(log.get_by_text(USER["content"], exact=True)).to_be_visible()
                page.locator('[data-page="dashboard"]').click()
                first_request_can_finish.set()
                page.get_by_role("button", name="Chat", exact=True).click()
                expect(log.get_by_text(ASSISTANT["content"], exact=True)).to_be_visible()
                expect(message).to_have_value("")

                message.fill(FOLLOW_UP["content"])
                send.click()
                expect(page.get_by_role("alert")).to_have_text("Chat could not get a reply. Try again.")
                expect(message).to_have_value(FOLLOW_UP["content"])
                send.click()
                expect(log.get_by_text("Indigo. <b>Plain text</b>", exact=True)).to_be_visible()
                expect(log.get_by_text(FOLLOW_UP["content"], exact=True)).to_have_count(1)
                expect(page.get_by_role("alert")).to_be_empty()
                self.assertEqual(requests, [[USER], [USER, ASSISTANT, FOLLOW_UP], [USER, ASSISTANT, FOLLOW_UP]])
                self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))

                reset.click()
                expect(page.get_by_text("Ask a question to start a conversation.")).to_be_visible()
                expect(log).to_be_hidden()
                self.assertEqual(len(browser_chat_requests), 3)
                for request in browser_chat_requests:
                    self.assertNotIn("authorization", request.headers)
                    self.assertNotIn(FIXTURE_TOKEN, request.post_data)
                self.assertEqual(page_errors, [])
            finally:
                browser.close()
