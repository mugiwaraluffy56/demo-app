import os
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

router = APIRouter(tags=["Chat"])
MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: MessageText


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[Message] = Field(min_length=1, max_length=21)

    @model_validator(mode="after")
    def validate_turns(self):
        if len(self.messages) % 2 == 0 or any(
            message.role != ("user" if index % 2 == 0 else "assistant")
            for index, message in enumerate(self.messages)
        ):
            raise ValueError("Messages must alternate between user and assistant and end with a user message")
        return self


class ChatReply(BaseModel):
    reply: str


def openai_client():
    return httpx.AsyncClient(timeout=30.0)


@router.post("/api/chat", response_model=ChatReply)
async def chat(request: ChatRequest):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "Chat is unavailable. Set OPENAI_API_KEY on the server and try again.")

    try:
        async with openai_client() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [message.model_dump() for message in request.messages],
                    "max_completion_tokens": 512,
                    "store": False,
                },
            )
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("Empty provider reply")
    except httpx.TimeoutException:
        raise HTTPException(504, "Chat took too long to respond. Try again.") from None
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 429:
            raise HTTPException(429, "Chat is busy or has reached its usage limit. Try again later.") from None
        raise HTTPException(502, "Chat could not get a reply. Try again.") from None
    except (httpx.RequestError, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(502, "Chat could not get a reply. Try again.") from None

    return ChatReply(reply=reply.strip()[:8000])
