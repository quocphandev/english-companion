"""Build the provider request (system prompt + recent messages) for a chat turn."""

from typing import Literal

from pydantic import BaseModel

from app.harness.prompts import SYSTEM_PROMPT_TEMPLATE, turn_reply_schema
from app.providers.ai_provider import ProviderMessage, ProviderRequest

MAX_HISTORY_MESSAGES = 20


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class TurnContext(BaseModel):
    """Everything the harness needs for one turn; filled in by the service layer."""

    level: Literal["A1", "A2", "B1", "B2"]
    correction_mode: Literal["learning", "conversation"]
    topic: str
    summary: str | None = None
    history: list[ChatTurn] = []
    user_text: str


def build_system_prompt(context: TurnContext) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        level=context.level,
        correction_mode=context.correction_mode,
        topic=context.topic,
        summary=context.summary or "(none)",
        schema=turn_reply_schema(),
    )


def build_messages(context: TurnContext) -> list[ProviderMessage]:
    """Keep the most recent history, start with a user turn, end with the new text."""
    recent = context.history[-MAX_HISTORY_MESSAGES:]
    messages = [ProviderMessage(role=turn.role, content=turn.text) for turn in recent]
    # The provider expects the conversation to start with a user message.
    while messages and messages[0].role == "assistant":
        messages.pop(0)
    messages.append(ProviderMessage(role="user", content=context.user_text))
    return messages


def build_request(context: TurnContext, max_tokens: int) -> ProviderRequest:
    return ProviderRequest(
        system=build_system_prompt(context),
        messages=build_messages(context),
        max_tokens=max_tokens,
    )
