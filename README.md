# TaskBoard

Install dependencies with `python -m pip install -r requirements.txt` and run
`uvicorn main:app --reload`. Open the app and select **Chat** in the sidebar.

Set `OPENAI_API_KEY` in the server process environment to enable Chat. The server
uses OpenAI's `gpt-4o-mini` model. The current transcript lives in the open page
until you start a new chat or reload. Up to ten previous exchanges are sent to
OpenAI as context for each new message.

## Chat tests

Run the API tests with `python -m unittest discover -s tests -p test_chat.py`.
For the browser test, install Playwright with `python -m pip install playwright`
and run `python -m playwright install chromium`. You can also set
`CHAT_TEST_CHROMIUM` to a system Chromium executable. Then run
`python -m unittest discover -s tests`. Both test suites use a deterministic
provider fixture and require no live credentials.
