"""Build the provider request for the end-of-session summary (FR10)."""

import json

from pydantic import BaseModel

from app.harness.context import ChatTurn
from app.harness.prompts import SUMMARY_SYSTEM_PROMPT
from app.providers.ai_provider import ProviderMessage, ProviderRequest
from app.schemas.ai import SummaryReply

# Keep the request small: the most recent turns, each cut to a reasonable length.
MAX_SUMMARY_TURNS = 40
MAX_TURN_CHARS = 500
SPEAKERS = {"user": "Learner", "assistant": "Chatbot"}


class SummaryContext(BaseModel):
    topic: str
    turns: list[ChatTurn]
    # Real mistakes found during the session, e.g. '"go" -> "went" (grammar)'.
    mistakes: list[str] = []


def build_summary_request(context: SummaryContext, max_tokens: int) -> ProviderRequest:
    system = SUMMARY_SYSTEM_PROMPT.format(
        schema=json.dumps(SummaryReply.model_json_schema(), indent=2)
    )
    lines = [f"Topic: <topic>{context.topic}</topic>", "Conversation:"]
    for turn in context.turns[-MAX_SUMMARY_TURNS:]:
        lines.append(f"{SPEAKERS[turn.role]}: {turn.text[:MAX_TURN_CHARS]}")
    if context.mistakes:
        lines.append("Mistakes found:")
        lines.extend(f"- {mistake}" for mistake in context.mistakes)
    # Everything said in the session is content: one user turn, never system.
    return ProviderRequest(
        system=system,
        messages=[ProviderMessage(role="user", content="\n".join(lines))],
        max_tokens=max_tokens,
        response_schema=SummaryReply.model_json_schema(),
    )
