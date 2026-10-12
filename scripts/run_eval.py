"""Run the fixed eval sentences through the REAL Gemini API and write a review file.

Only for manual quality review (prompt or model changes). Never run by pytest.

    PowerShell:  $env:RUN_LIVE_AI="1"; python -m scripts.run_eval --limit 30
    Bash:        RUN_LIVE_AI=1 python -m scripts.run_eval --limit 30

Each sentence is one chat turn (at most 2 provider calls). Every turn is
recorded in ai_runs (operation "eval") and counts toward DAILY_AI_LIMIT.
The run stops early on a daily limit, a rate limit or a configuration error.
"""

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_engine
from app.dependencies import create_provider
from app.harness.chat_harness import ChatHarness, TurnResult
from app.harness.context import TurnContext
from app.harness.prompts import PROMPT_VERSION
from app.repositories.ai_run_repository import AiRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import CorrectionOut
from app.services.correction_view import build_correction_view

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = PROJECT_ROOT / "tests" / "data" / "eval_sentences.json"
RESULTS_DIR = PROJECT_ROOT / "eval_results"
# Errors after which more calls are pointless or harmful.
STOP_CODES = {
    "ai_quota_exhausted",
    "ai_rate_limited",
    "ai_auth_failed",
    "ai_model_not_found",
}


def load_eval_set(path: Path = EVAL_SET) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the eval sentences on the real Gemini API."
    )
    parser.add_argument(
        "--limit", type=int, default=30, help="max sentences to run (default 30)"
    )
    parser.add_argument(
        "--delay", type=float, default=4.0, help="seconds between sentences (default 4)"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    # Test-only style switch, deliberately outside Settings so the app can never turn it on.
    if os.environ.get("RUN_LIVE_AI") != "1":
        print(
            "Refusing to call the real Gemini API: set RUN_LIVE_AI=1 to run the eval."
        )
        return 2

    settings = get_settings()
    provider = create_provider(settings.model_copy(update={"ai_provider": "gemini"}))
    harness = ChatHarness(provider, settings.ai_max_output_tokens)
    sentences = load_eval_set()[: max(args.limit, 0)]

    with SessionLocal(bind=get_engine()) as session:
        timezone = (
            ConversationRepository(session).get_or_create_default_profile().timezone
        )
        session.commit()
        results, stop_reason = evaluate(
            sentences,
            harness,
            session,
            daily_limit=settings.daily_ai_limit,
            timezone=timezone,
            delay=args.delay,
        )

    report_path = write_report(
        results, settings.gemini_model, settings.gemini_thinking_level, stop_reason
    )
    print(f"Done: {len(results)} sentence(s). {stop_reason}".strip())
    print(f"Review file: {report_path}")
    return 0


def evaluate(
    sentences: list[dict[str, str]],
    harness: ChatHarness,
    session: Session,
    *,
    daily_limit: int,
    timezone: str,
    delay: float,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[tuple[dict[str, str], TurnResult]], str]:
    """Run sentences one by one; stop on the daily limit or a stop-worthy error."""
    runs = AiRunRepository(session)
    results: list[tuple[dict[str, str], TurnResult]] = []
    for index, item in enumerate(sentences):
        used = runs.count_calls_today(timezone)
        if used >= daily_limit:
            return results, f"DAILY_AI_LIMIT reached ({used}/{daily_limit})"
        print(f"[{index + 1}/{len(sentences)}] {item['id']} ...", flush=True)
        result = harness.run_turn(to_context(item))
        record_run(runs, result, harness.provider_name, harness.model_name)
        session.commit()
        results.append((item, result))
        if result.error is not None and result.error.code in STOP_CODES:
            return results, f"stopped on {result.error.code}"
        if index + 1 < len(sentences):
            sleep(delay)
    return results, ""


def to_context(item: dict[str, str]) -> TurnContext:
    return TurnContext(
        level=item["level"],
        correction_mode="learning",
        topic=item["topic"],
        user_text=item["text"],
    )


def record_run(
    runs: AiRunRepository, result: TurnResult, provider: str, model: str
) -> None:
    runs.add_run(
        operation="eval",
        request_id=None,
        provider=provider,
        model=model,
        prompt_version=PROMPT_VERSION,
        status=result.status,
        error_code=result.error.code if result.error else None,
        call_count=result.attempts,
        duration_ms=result.duration_ms,
    )


def write_report(
    results: list[tuple[dict[str, str], TurnResult]],
    model: str,
    thinking_level: str,
    stop_reason: str,
) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"{stamp}-{PROMPT_VERSION}.md"
    header = [
        f"# Eval {stamp} UTC",
        "",
        f"- Prompt: `{PROMPT_VERSION}` · Model: `{model}` · Thinking: `{thinking_level or 'default'}`",
        f"- Sentences: {len(results)}" + (f" · {stop_reason}" if stop_reason else ""),
        "- Chấm mỗi câu: Đạt / Không đạt, kèm ghi chú. Không so khớp nguyên văn.",
        "",
    ]
    body = [line for item, result in results for line in format_entry(item, result)]
    path.write_text("\n".join(header + body) + "\n", encoding="utf-8")
    return path


def format_entry(item: dict[str, str], result: TurnResult) -> list[str]:
    """Markdown block for one sentence: input, expectation, AI output, blank verdict."""
    lines = [
        f"## {item['id']} · {item['category']} · {item['level']} · {item['topic']}",
        "",
        f"**Câu:** {item['text']}",
        "",
        f"**Kỳ vọng:** {item['expectation_vi']}",
        "",
        f"**Kết quả:** {result.status} · {result.attempts} call · {result.duration_ms} ms",
    ]
    if result.reply is None:
        error = result.error.code if result.error else "unknown"
        lines += ["", f"**Lỗi:** `{error}`"]
    else:
        reply = result.reply
        corrections = [
            CorrectionOut.model_validate(c.model_dump()) for c in reply.corrections
        ]
        view = build_correction_view(item["text"], corrections)
        lines += ["", f"**reply_en:** {reply.reply_en}", ""]
        lines += format_corrections(corrections)
        if view is not None and view.corrected is not None:
            lines += [
                "",
                "**Câu sửa:** " + "".join(segment.text for segment in view.corrected),
            ]
        if reply.suggested_words:
            words = ", ".join(
                f"{w.text} ({w.meaning_vi})" for w in reply.suggested_words
            )
            lines += ["", f"**suggested_words:** {words}"]
    lines += ["", "**Đánh giá:** ☐ Đạt ☐ Không đạt — Ghi chú:", "", "---", ""]
    return lines


def format_corrections(corrections: list[Any]) -> list[str]:
    if not corrections:
        return ["**corrections:** (không có)"]
    lines = ["**corrections:**", ""]
    for c in corrections:
        lines.append(
            f"- [{c.category}] `{c.original_span}` → `{c.corrected_text}`: {c.explanation_vi}"
        )
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
