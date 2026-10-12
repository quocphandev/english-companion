"""FR02 / AC02–AC04 with scripted AI output (no real API).

These tests prove the pipeline: corrections are stored, shaped and shown or
hidden per mode. Whether the real AI corrects well is reviewed by a person
with the fixed eval set (scripts/run_eval.py).
"""

import json
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.harness.prompts import PROMPT_VERSION
from app.models import Correction
from tests.fakes import ScriptedProvider
from tests.integration.conftest import ProviderSetter

SENTENCE_WITH_ERROR = "Yesterday I go to work."
GO_WENT = {
    "category": "grammar",
    "original_span": "I go",
    "corrected_text": "I went",
    "explanation_vi": "Hôm qua là quá khứ nên dùng 'went'.",
}
STYLE_TIP = {
    "category": "naturalness",
    "original_span": "very like",
    "corrected_text": "really like",
    "explanation_vi": "Tùy chọn: 'really like' tự nhiên hơn.",
}


def ai_reply(*corrections: dict[str, str]) -> str:
    return json.dumps(
        {"reply_en": "Nice! What did you do?", "corrections": list(corrections)}
    )


def create_conversation(client: TestClient, mode: str) -> int:
    response = client.post(
        "/api/conversations", json={"topic": "work", "correction_mode": mode}
    )
    return response.json()["conversation_id"]


def send(
    client: TestClient, conversation_id: int, text: str, request_id: str = "req-1"
) -> Any:
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"request_id": request_id, "text": text},
    )
    assert response.status_code == 200
    return response.json()


def sentence(segments: list[dict[str, Any]]) -> str:
    return "".join(segment["text"] for segment in segments)


# --- AC02: a wrong sentence gets the right correction --------------------------


def test_ac02_error_is_stored_and_shown_as_corrected_sentence(
    client: TestClient, db_session: Session, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([ai_reply(GO_WENT)]))
    conversation_id = create_conversation(client, "learning")

    body = send(client, conversation_id, SENTENCE_WITH_ERROR)

    view = body["correction_view"]
    assert sentence(view["original"]) == SENTENCE_WITH_ERROR
    assert sentence(view["corrected"]) == "Yesterday I went to work."
    assert [s["text"] for s in view["corrected"] if s["changed"]] == ["I went"]
    assert view["errors"][0]["explanation_vi"] == GO_WENT["explanation_vi"]
    stored = db_session.scalar(select(Correction))
    assert stored is not None
    assert (stored.category, stored.corrected_text) == ("grammar", "I went")
    assert stored.prompt_version == PROMPT_VERSION == "chat-turn-v2"


# --- AC03: correct sentences get no fake errors; style tips are separate ---------


def test_ac03_correct_sentence_has_no_card(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([ai_reply()]))
    conversation_id = create_conversation(client, "learning")

    body = send(client, conversation_id, "I went to work yesterday.")
    html = client.get(f"/conversations/{conversation_id}").text

    assert body["corrections"] == []
    assert body["correction_view"] is None
    assert "correction-card" not in html


def test_ac03_style_tip_is_optional_and_separate(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([ai_reply(STYLE_TIP)]))
    conversation_id = create_conversation(client, "learning")

    body = send(client, conversation_id, "I very like coffee.")
    html = client.get(f"/conversations/{conversation_id}").text

    view = body["correction_view"]
    assert view["errors"] == []
    assert view["corrected"] is None
    assert [s["category"] for s in view["suggestions"]] == ["naturalness"]
    assert "Gợi ý diễn đạt tự nhiên hơn (tùy chọn)" in html
    assert "Câu sửa" not in html


# --- AC04: conversation mode hides the card, "Xem lỗi" still opens it -----------


def test_ac04_learning_mode_opens_the_card(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([ai_reply(GO_WENT)]))
    conversation_id = create_conversation(client, "learning")
    send(client, conversation_id, SENTENCE_WITH_ERROR)

    html = client.get(f"/conversations/{conversation_id}").text

    assert '<details class="correction-card correction-card-learning" open>' in html
    assert "Gợi ý sửa (1)" in html


def test_ac04_conversation_mode_closes_the_card_behind_xem_loi(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([ai_reply(GO_WENT)]))
    conversation_id = create_conversation(client, "conversation")

    body = send(client, conversation_id, SENTENCE_WITH_ERROR)
    html = client.get(f"/conversations/{conversation_id}").text

    assert '<details class="correction-card correction-card-conversation">' in html
    assert "Xem lỗi (1)" in html
    # Still reachable: the content is in the page and in the API response.
    assert GO_WENT["explanation_vi"].replace("'", "&#39;") in html
    assert body["corrections"][0]["corrected_text"] == "I went"
    assert 'data-correction-mode="conversation"' in html


def test_ac04_each_conversation_keeps_its_own_mode(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    use_provider(ScriptedProvider([ai_reply(GO_WENT)]))
    old_id = create_conversation(client, "conversation")
    send(client, old_id, SENTENCE_WITH_ERROR)
    create_conversation(client, "learning")  # newer conversation, other mode

    html = client.get(f"/conversations/{old_id}").text

    assert "correction-card-conversation" in html
    assert "Xem lỗi (1)" in html


# --- AI output is untrusted: always escaped -------------------------------------


def test_ai_correction_text_is_escaped(
    client: TestClient, use_provider: ProviderSetter
) -> None:
    hostile = {**GO_WENT, "explanation_vi": '<img src=x onerror="alert(1)">'}
    use_provider(ScriptedProvider([ai_reply(hostile)]))
    conversation_id = create_conversation(client, "learning")
    send(client, conversation_id, SENTENCE_WITH_ERROR)

    html = client.get(f"/conversations/{conversation_id}").text

    assert '<img src=x onerror="alert(1)">' not in html
    assert "&lt;img src=x onerror=&#34;alert(1)&#34;&gt;" in html
