import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.ai import TurnReply


def make_correction(**overrides: Any) -> dict[str, Any]:
    correction = {
        "category": "grammar",
        "original_span": "I go",
        "corrected_text": "I went",
        "explanation_vi": "Dùng quá khứ đơn.",
    }
    return {**correction, **overrides}


def test_valid_reply_is_parsed() -> None:
    payload = {
        "reply_en": "Nice! What did you do next?",
        "corrections": [make_correction()],
        "suggested_words": [{"text": "commute", "meaning_vi": "đi lại"}],
    }

    reply = TurnReply.model_validate_json(json.dumps(payload))

    assert reply.reply_en == "Nice! What did you do next?"
    assert reply.corrections[0].category == "grammar"
    assert reply.suggested_words[0].text == "commute"


def test_missing_lists_default_to_empty() -> None:
    reply = TurnReply.model_validate_json('{"reply_en": "Hello!"}')

    assert reply.corrections == []
    assert reply.suggested_words == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing reply_en"),
        pytest.param({"reply_en": "   "}, id="blank reply_en"),
        pytest.param(
            {"reply_en": "Hi", "corrections": [make_correction()] * 4},
            id="more than 3 corrections",
        ),
        pytest.param(
            {"reply_en": "Hi", "corrections": [make_correction(category="style")]},
            id="unknown category",
        ),
        pytest.param(
            {"reply_en": "Hi", "suggested_words": [{"text": "x"}]},
            id="word without meaning",
        ),
    ],
)
def test_invalid_reply_is_rejected(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        TurnReply.model_validate(payload)


def test_non_json_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TurnReply.model_validate_json("Sure! Here is my answer.")
