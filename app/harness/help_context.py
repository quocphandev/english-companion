"""Build the provider request for "Giúp tôi" (FR03): settings + recent turns + the help ask."""

import json
from typing import Literal

from pydantic import BaseModel

from app.harness.context import ChatTurn, history_messages
from app.harness.prompts import HELP_MODE_INSTRUCTIONS, HELP_SYSTEM_PROMPT_TEMPLATE
from app.providers.ai_provider import ProviderMessage, ProviderRequest
from app.schemas.ai import HelpReply

HelpMode = Literal["words", "starter", "sample", "intent"]
HELP_LEVEL_MODES: dict[int, HelpMode] = {1: "words", 2: "starter", 3: "sample"}


class HelpContext(BaseModel):
    level: Literal["A1", "A2", "B1", "B2"]
    topic: str
    summary: str | None = None
    history: list[ChatTurn] = []
    mode: HelpMode
    intent_vi: str | None = None


def help_mode_for(level: int, intent_vi: str | None) -> HelpMode:
    """A Vietnamese idea always means "say this in English"; otherwise the level decides."""
    return "intent" if intent_vi else HELP_LEVEL_MODES[level]


def build_help_request(context: HelpContext, max_tokens: int) -> ProviderRequest:
    system = HELP_SYSTEM_PROMPT_TEMPLATE.format(
        level=context.level,
        topic=context.topic,
        summary=context.summary or "(none)",
        mode_instruction=HELP_MODE_INSTRUCTIONS[context.mode],
        schema=json.dumps(HelpReply.model_json_schema(), indent=2),
    )
    messages = history_messages(context.history)
    # The learner's own words (the Vietnamese idea) go in a user turn, never in system.
    if context.intent_vi:
        ask = f"I'm stuck. This is what I want to say, in Vietnamese: <intent>{context.intent_vi}</intent>"
    else:
        ask = "I'm stuck. Please help me continue the conversation."
    messages.append(ProviderMessage(role="user", content=ask))
    return ProviderRequest(
        system=system,
        messages=messages,
        max_tokens=max_tokens,
        response_schema=HelpReply.model_json_schema(),
    )
