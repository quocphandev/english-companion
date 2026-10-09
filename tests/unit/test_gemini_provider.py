"""GeminiProvider with a fake client: no network, no real API calls."""

import json
import logging
from typing import Any

import httpx
import pytest
from google.genai import errors, types

from app.providers.ai_provider import ProviderMessage, ProviderRequest
from app.providers.errors import ProviderError
from app.providers.gemini_provider import GeminiProvider, to_gemini_schema
from app.schemas.ai import TurnReply

FAKE_KEY = "test-key-not-real-123"
VALID_JSON = '{"reply_en": "Nice!", "corrections": [], "suggested_words": []}'


class FakeModels:
    """Stands in for client.models: returns or raises a prepared result."""

    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class FakeClient:
    def __init__(self, result: Any) -> None:
        self.models = FakeModels(result)


def make_provider(result: Any, **overrides: Any) -> tuple[GeminiProvider, FakeClient]:
    client = FakeClient(result)
    options: dict[str, Any] = {
        "api_key": FAKE_KEY,
        "model": "gemini-test-model",
        "timeout_seconds": 30,
        "thinking_level": "minimal",
        "client": client,
    }
    return GeminiProvider(**{**options, **overrides}), client


def make_request(schema: dict[str, Any] | None = None) -> ProviderRequest:
    return ProviderRequest(
        system="SYSTEM RULES",
        messages=[
            ProviderMessage(role="user", content="I like coffee."),
            ProviderMessage(role="assistant", content="Nice!"),
            ProviderMessage(role="user", content="Yesterday I go to work."),
        ],
        max_tokens=800,
        response_schema=schema,
    )


def text_response(
    text: str, finish_reason: str = "STOP"
) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model", parts=[types.Part.from_text(text=text)]
                ),
                finish_reason=finish_reason,
            )
        ]
    )


def api_error(
    error_class: type[errors.APIError],
    http_code: int,
    status: str,
    message: str,
    details: Any = None,
) -> errors.APIError:
    body: dict[str, Any] = {
        "error": {"code": http_code, "status": status, "message": message}
    }
    if details is not None:
        body["error"]["details"] = details
    return error_class(http_code, body)


def quota_details(quota_id: str) -> list[dict[str, Any]]:
    return [
        {
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": quota_id}],
        }
    ]


# --- Successful call ------------------------------------------------------------


def test_successful_call_returns_text_and_sends_expected_request() -> None:
    schema = TurnReply.model_json_schema()
    provider, client = make_provider(text_response(VALID_JSON))

    response = provider.complete(make_request(schema))

    assert response.text == VALID_JSON
    call = client.models.calls[0]
    assert call["model"] == "gemini-test-model"
    assert [content.role for content in call["contents"]] == ["user", "model", "user"]
    assert call["contents"][2].parts[0].text == "Yesterday I go to work."
    config = call["config"]
    assert config.system_instruction == "SYSTEM RULES"
    assert config.max_output_tokens == 800
    assert config.http_options.timeout == 30_000
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == to_gemini_schema(schema)
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL


def test_user_text_is_never_put_in_the_system_instruction() -> None:
    provider, client = make_provider(text_response(VALID_JSON))

    provider.complete(make_request())

    config = client.models.calls[0]["config"]
    assert "Yesterday I go to work." not in config.system_instruction


def test_without_schema_or_thinking_level_those_options_are_not_sent() -> None:
    provider, client = make_provider(text_response("plain"), thinking_level="")

    provider.complete(make_request(schema=None))

    config = client.models.calls[0]["config"]
    assert config.response_mime_type is None
    assert config.response_json_schema is None
    assert config.thinking_config is None


def test_cut_off_answer_is_returned_for_the_harness_to_repair() -> None:
    provider, _ = make_provider(
        text_response('{"reply_en": "Hel', finish_reason="MAX_TOKENS")
    )

    assert provider.complete(make_request()).text == '{"reply_en": "Hel'


# --- Schema cleaning ------------------------------------------------------------


def find_keys(node: Any) -> set[str]:
    if isinstance(node, dict):
        keys = set(node)
        for value in node.values():
            keys |= find_keys(value)
        return keys
    if isinstance(node, list):
        return set().union(*(find_keys(item) for item in node)) if node else set()
    return set()


def test_schema_drops_unsupported_keywords_but_keeps_property_names() -> None:
    cleaned = to_gemini_schema(TurnReply.model_json_schema())

    keys = find_keys(cleaned)
    assert "minLength" not in keys
    assert "default" not in keys
    assert set(cleaned["properties"]) == {"reply_en", "corrections", "suggested_words"}
    assert cleaned["properties"]["corrections"]["maxItems"] == 3
    assert "enum" in json.dumps(cleaned["$defs"]["Correction"])


# --- Errors before any call -----------------------------------------------------


def test_missing_key_fails_without_calling_the_api() -> None:
    provider, client = make_provider(text_response(VALID_JSON), api_key="")

    with pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    assert caught.value.code == "ai_auth_failed"
    assert caught.value.retryable is False
    assert client.models.calls == []


def test_missing_model_fails_without_calling_the_api() -> None:
    provider, client = make_provider(text_response(VALID_JSON), model="")

    with pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    assert caught.value.code == "ai_model_not_found"
    assert client.models.calls == []


# --- SDK and network errors -----------------------------------------------------


@pytest.mark.parametrize(
    ("raised", "expected_code", "expected_retryable"),
    [
        pytest.param(
            api_error(
                errors.ClientError,
                400,
                "INVALID_ARGUMENT",
                "API key not valid. Please pass a valid API key.",
            ),
            "ai_auth_failed",
            False,
            id="400 invalid key",
        ),
        pytest.param(
            api_error(
                errors.ClientError,
                401,
                "UNAUTHENTICATED",
                "Request had invalid credentials.",
            ),
            "ai_auth_failed",
            False,
            id="401",
        ),
        pytest.param(
            api_error(
                errors.ClientError, 403, "PERMISSION_DENIED", "Permission denied."
            ),
            "ai_auth_failed",
            False,
            id="403",
        ),
        pytest.param(
            api_error(errors.ClientError, 404, "NOT_FOUND", "models/x is not found."),
            "ai_model_not_found",
            False,
            id="404 model",
        ),
        pytest.param(
            api_error(
                errors.ClientError,
                429,
                "RESOURCE_EXHAUSTED",
                "Quota exceeded.",
                quota_details("GenerateRequestsPerMinutePerProjectPerModel-FreeTier"),
            ),
            "ai_rate_limited",
            True,
            id="429 per minute",
        ),
        pytest.param(
            api_error(
                errors.ClientError,
                429,
                "RESOURCE_EXHAUSTED",
                "Quota exceeded.",
                quota_details("GenerateRequestsPerDayPerProjectPerModel-FreeTier"),
            ),
            "ai_quota_exhausted",
            False,
            id="429 per day",
        ),
        pytest.param(
            api_error(
                errors.ClientError, 400, "INVALID_ARGUMENT", "Invalid JSON payload."
            ),
            "ai_bad_request",
            False,
            id="400 other",
        ),
        pytest.param(
            api_error(errors.ServerError, 500, "INTERNAL", "Internal error."),
            "ai_unavailable",
            True,
            id="500",
        ),
        pytest.param(
            api_error(
                errors.ServerError, 503, "UNAVAILABLE", "The model is overloaded."
            ),
            "ai_unavailable",
            True,
            id="503 overloaded",
        ),
        pytest.param(
            api_error(
                errors.ServerError, 504, "DEADLINE_EXCEEDED", "Deadline exceeded."
            ),
            "ai_timeout",
            True,
            id="504",
        ),
        pytest.param(
            httpx.ReadTimeout("timed out"), "ai_timeout", True, id="client timeout"
        ),
        pytest.param(
            httpx.ConnectError("connection refused"),
            "ai_network_error",
            True,
            id="network",
        ),
    ],
)
def test_errors_become_structured_provider_errors(
    raised: BaseException, expected_code: str, expected_retryable: bool
) -> None:
    provider, client = make_provider(raised)

    with pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    assert caught.value.code == expected_code
    assert caught.value.retryable is expected_retryable
    assert caught.value.message_vi
    assert len(client.models.calls) == 1  # never retried


# --- Blocked or empty answers ---------------------------------------------------


def test_prompt_blocked_by_safety_filter() -> None:
    blocked = types.GenerateContentResponse(
        candidates=[],
        prompt_feedback=types.GenerateContentResponsePromptFeedback(
            block_reason="SAFETY"
        ),
    )
    provider, _ = make_provider(blocked)

    with pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    assert caught.value.code == "ai_blocked"
    assert caught.value.retryable is False


@pytest.mark.parametrize(
    "finish_reason", ["SAFETY", "PROHIBITED_CONTENT", "RECITATION"]
)
def test_answer_stopped_by_content_policy(finish_reason: str) -> None:
    stopped = types.GenerateContentResponse(
        candidates=[types.Candidate(finish_reason=finish_reason)]
    )
    provider, _ = make_provider(stopped)

    with pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    assert caught.value.code == "ai_blocked"


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(types.GenerateContentResponse(candidates=[]), id="no candidates"),
        pytest.param(text_response("   "), id="blank text"),
    ],
)
def test_empty_answer(response: types.GenerateContentResponse) -> None:
    provider, _ = make_provider(response)

    with pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    assert caught.value.code == "ai_empty_response"
    assert caught.value.retryable is True


# --- Nothing secret leaks -------------------------------------------------------


def test_errors_and_logs_never_contain_the_key_or_raw_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_message = f"API key not valid: {FAKE_KEY}"
    provider, _ = make_provider(
        api_error(errors.ClientError, 400, "INVALID_ARGUMENT", secret_message)
    )

    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderError) as caught:
        provider.complete(make_request())

    error = caught.value
    assert error.__cause__ is None  # original SDK error is not chained
    for text in (
        str(error),
        error.message_vi,
        error.to_error_body().model_dump_json(),
        caplog.text,
    ):
        assert FAKE_KEY not in text
        assert "API key not valid" not in text


def test_real_client_cannot_be_created_in_automated_tests() -> None:
    # No injected client: the provider would build a real one, which tests/conftest.py forbids.
    provider = GeminiProvider(
        api_key=FAKE_KEY, model="gemini-test-model", timeout_seconds=30
    )

    with pytest.raises(RuntimeError, match="must not create a real Gemini client"):
        provider.complete(make_request())
