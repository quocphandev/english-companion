"""The fixed eval set and the eval script, without ever calling the real API."""

from collections import Counter

import pytest

from app.harness.chat_harness import TurnResult
from app.schemas.ai import Correction, TurnReply
from scripts import run_eval

EXPECTED_COUNTS = {"correct": 8, "incorrect": 10, "ambiguous": 6, "mixed": 6}


def test_eval_set_has_30_sentences_in_the_planned_mix() -> None:
    items = run_eval.load_eval_set()

    assert len(items) == 30
    assert Counter(item["category"] for item in items) == EXPECTED_COUNTS


def test_eval_items_are_complete_and_unique() -> None:
    items = run_eval.load_eval_set()

    assert len({item["id"] for item in items}) == len(items)
    for item in items:
        assert item["level"] in {"A1", "A2", "B1", "B2"}
        for field in ("text", "topic", "expectation_vi"):
            assert item[field].strip(), f"{item['id']} has an empty {field}"


def test_script_refuses_without_the_live_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("RUN_LIVE_AI", raising=False)

    assert run_eval.main(["--limit", "1"]) == 2
    assert "RUN_LIVE_AI=1" in capsys.readouterr().out


def test_report_entry_shows_output_and_a_blank_verdict() -> None:
    item = run_eval.load_eval_set()[8]  # i01: "Yesterday I go to work."
    reply = TurnReply(
        reply_en="Nice! What did you do there?",
        corrections=[
            Correction(
                category="grammar",
                original_span="go",
                corrected_text="went",
                explanation_vi="Quá khứ đơn.",
            )
        ],
    )
    result = TurnResult(status="succeeded", reply=reply, attempts=1, duration_ms=900)

    text = "\n".join(run_eval.format_entry(item, result))

    assert item["text"] in text
    assert item["expectation_vi"] in text
    assert "`go` → `went`" in text
    assert "**Câu sửa:** Yesterday I went to work." in text
    assert "☐ Đạt ☐ Không đạt" in text


def test_report_entry_for_a_failed_turn_shows_the_error_code() -> None:
    item = run_eval.load_eval_set()[0]
    result = TurnResult(status="failed", attempts=2)

    text = "\n".join(run_eval.format_entry(item, result))

    assert "**Lỗi:** `unknown`" in text
