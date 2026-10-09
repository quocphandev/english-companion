from typing import Any

from app.harness.context import (
    MAX_HISTORY_MESSAGES,
    ChatTurn,
    TurnContext,
    build_request,
)
from app.schemas.ai import TurnReply


def make_context(**overrides: Any) -> TurnContext:
    values: dict[str, Any] = {
        "level": "A2",
        "correction_mode": "learning",
        "topic": "coffee shop",
        "user_text": "Yesterday I go to work.",
    }
    return TurnContext(**{**values, **overrides})


def alternating_history(count: int) -> list[ChatTurn]:
    return [
        ChatTurn(role="user" if i % 2 == 0 else "assistant", text=f"turn {i}")
        for i in range(count)
    ]


def test_keeps_only_recent_history_and_appends_user_text() -> None:
    context = make_context(history=alternating_history(30))

    request = build_request(context, max_tokens=800)

    assert len(request.messages) == MAX_HISTORY_MESSAGES + 1
    assert request.messages[0].content == "turn 10"
    assert request.messages[-1].role == "user"
    assert request.messages[-1].content == "Yesterday I go to work."
    assert request.max_tokens == 800


def test_conversation_starts_with_user_message() -> None:
    history = [
        ChatTurn(role="assistant", text="Hi! What did you do yesterday?"),
        ChatTurn(role="user", text="I worked."),
        ChatTurn(role="assistant", text="Nice."),
    ]

    request = build_request(make_context(history=history), max_tokens=800)

    assert [m.content for m in request.messages] == [
        "I worked.",
        "Nice.",
        "Yesterday I go to work.",
    ]


def test_system_prompt_has_settings_but_not_user_text() -> None:
    request = build_request(make_context(), max_tokens=800)

    assert "A2" in request.system
    assert "learning" in request.system
    assert "coffee shop" in request.system
    assert "reply_en" in request.system
    assert "Yesterday I go to work." not in request.system


def test_request_asks_for_the_turn_reply_schema() -> None:
    request = build_request(make_context(), max_tokens=800)

    assert request.response_schema == TurnReply.model_json_schema()
