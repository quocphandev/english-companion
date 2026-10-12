"""The eval loop on the TEST database with scripted providers (never the real API)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.harness.chat_harness import ChatHarness
from app.models import AiRun
from scripts import run_eval
from tests.fakes import FailingProvider, ScriptedProvider

VALID_JSON = '{"reply_en": "Nice!", "corrections": []}'
TIMEZONE = "Asia/Ho_Chi_Minh"


def sentences(count: int) -> list[dict[str, str]]:
    return run_eval.load_eval_set()[:count]


def no_sleep(_: float) -> None:
    return None


def test_each_sentence_is_recorded_as_an_eval_run(db_session: Session) -> None:
    harness = ChatHarness(ScriptedProvider([VALID_JSON] * 3), max_output_tokens=800)

    results, stop_reason = run_eval.evaluate(
        sentences(3),
        harness,
        db_session,
        daily_limit=100,
        timezone=TIMEZONE,
        delay=0,
        sleep=no_sleep,
    )

    assert stop_reason == ""
    assert [result.status for _, result in results] == ["succeeded"] * 3
    runs = db_session.scalars(select(AiRun)).all()
    assert [run.operation for run in runs] == ["eval"] * 3


def test_stops_when_the_daily_limit_is_reached(db_session: Session) -> None:
    harness = ChatHarness(ScriptedProvider([VALID_JSON] * 5), max_output_tokens=800)

    results, stop_reason = run_eval.evaluate(
        sentences(5),
        harness,
        db_session,
        daily_limit=2,
        timezone=TIMEZONE,
        delay=0,
        sleep=no_sleep,
    )

    assert len(results) == 2
    assert stop_reason.startswith("DAILY_AI_LIMIT reached")


def test_stops_on_a_rate_limit_without_retrying(db_session: Session) -> None:
    provider = FailingProvider("ai_rate_limited")
    harness = ChatHarness(provider, max_output_tokens=800)

    results, stop_reason = run_eval.evaluate(
        sentences(5),
        harness,
        db_session,
        daily_limit=100,
        timezone=TIMEZONE,
        delay=0,
        sleep=no_sleep,
    )

    assert len(results) == 1
    assert provider.calls == 1
    assert stop_reason == "stopped on ai_rate_limited"
