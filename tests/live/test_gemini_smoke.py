"""Smoke test against the REAL Gemini API. Skipped unless RUN_LIVE_AI=1.

Run manually, only when asked (PowerShell):
    $env:RUN_LIVE_AI="1"; pytest tests/live -s
At most MAX_LIVE_CALLS requests are sent. Results are printed for a human to
review; quality is not asserted word for word.
"""

import logging
import os

import pytest

from app.config import get_settings
from app.harness.context import TurnContext, build_request
from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.providers.errors import ProviderError
from app.providers.gemini_provider import GeminiProvider
from app.schemas.ai import TurnReply

MAX_LIVE_CALLS = 3

pytestmark = [
    pytest.mark.live_ai,
    # Test-only switch, deliberately outside Settings so the app can never turn it on.
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_AI") != "1",
        reason="Live Gemini smoke test: set RUN_LIVE_AI=1 to run it.",
    ),
]


class CallBudget(AIProvider):
    """Wraps a provider and refuses to go over the shared call budget."""

    used = 0

    def __init__(self, inner: AIProvider) -> None:
        self._inner = inner

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if CallBudget.used >= MAX_LIVE_CALLS:
            raise AssertionError(f"Live smoke test exceeded {MAX_LIVE_CALLS} calls")
        CallBudget.used += 1
        print(f"\n--- live call {CallBudget.used}/{MAX_LIVE_CALLS}")
        return self._inner.complete(request)


def real_provider(api_key: str | None = None) -> AIProvider:
    settings = get_settings()
    if not settings.gemini_api_key.get_secret_value() or not settings.gemini_model:
        pytest.skip("GEMINI_API_KEY and GEMINI_MODEL must be set in .env")
    return CallBudget(
        GeminiProvider(
            api_key=api_key or settings.gemini_api_key.get_secret_value(),
            model=settings.gemini_model,
            timeout_seconds=settings.ai_timeout_seconds,
            thinking_level=settings.gemini_thinking_level,
        )
    )


def structured_request(user_text: str) -> ProviderRequest:
    context = TurnContext(
        level="A2", correction_mode="learning", topic="work", user_text=user_text
    )
    request = build_request(context, get_settings().ai_max_output_tokens)
    return request.model_copy(update={"response_schema": TurnReply.model_json_schema()})


def show_reply(raw_text: str) -> TurnReply:
    reply = TurnReply.model_validate_json(raw_text)
    print(reply.model_dump_json(indent=2))
    return reply


def test_sentence_with_error_returns_valid_turn_reply() -> None:
    settings = get_settings()
    print(
        f"\nmodel={settings.gemini_model} thinking={settings.gemini_thinking_level or '(default)'}"
    )
    response = real_provider().complete(structured_request("Yesterday I go to work."))

    reply = show_reply(response.text)

    assert reply.reply_en
    assert len(reply.corrections) <= 3


def test_correct_sentence_is_answered() -> None:
    response = real_provider().complete(
        structured_request("I went to a coffee shop with my friend yesterday.")
    )

    reply = show_reply(response.text)

    # AC03: a correct sentence should not get invented errors (a human reviews this).
    print(
        f"real errors reported: {[c for c in reply.corrections if c.category != 'naturalness']}"
    )
    assert reply.reply_en


def test_invalid_key_maps_to_auth_error(caplog: pytest.LogCaptureFixture) -> None:
    provider = real_provider(api_key="invalid-key-for-smoke-test")

    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError) as caught:
        provider.complete(structured_request("Hello."))

    print(f"error code={caught.value.code} retryable={caught.value.retryable}")
    print(f"logged: {[r.getMessage() for r in caplog.records]}")
    assert caught.value.code == "ai_auth_failed"
