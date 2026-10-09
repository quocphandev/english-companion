"""Gemini API provider, using Google's official SDK (package google-genai).

One call = one stateless `models.generate_content` request: the conversation
history is sent every time; Google keeps no conversation state for us.
"""

import logging
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.providers.errors import ProviderError

logger = logging.getLogger(__name__)

# Gemini calls the AI side of a conversation "model", not "assistant".
GEMINI_ROLES = {"user": "user", "assistant": "model"}

# JSON Schema keywords supported by Gemini structured output (response_json_schema).
# Others (e.g. minLength, default) are dropped; Pydantic still checks them later.
SUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "$id",
        "$defs",
        "$ref",
        "$anchor",
        "type",
        "format",
        "title",
        "description",
        "enum",
        "items",
        "prefixItems",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "anyOf",
        "oneOf",
        "properties",
        "additionalProperties",
        "required",
        "propertyOrdering",
    }
)

# finish_reason values meaning the answer was withheld by a content policy.
BLOCKED_FINISH_REASONS = frozenset(
    {"SAFETY", "RECITATION", "LANGUAGE", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}
)


class GeminiProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        thinking_level: str = "",
        client: Any | None = None,
    ) -> None:
        """`client` lets tests inject a fake; by default a real one is created lazily."""
        self._api_key = api_key
        self._model = model
        self._timeout_ms = timeout_seconds * 1000
        self._thinking_level = thinking_level
        self._client = client

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        # Checked before any network call, so a missing key costs nothing.
        if not self._api_key:
            raise ProviderError("ai_auth_failed")
        if not self._model:
            raise ProviderError("ai_model_not_found")
        try:
            response = self._get_client().models.generate_content(
                model=self._model,
                contents=to_gemini_contents(request),
                config=self._build_config(request),
            )
        except errors.APIError as error:
            # Log status only: the original message stays on the server side.
            logger.warning(
                "Gemini API error: http=%s status=%s", error.code, error.status
            )
            raise map_api_error(error) from None
        except httpx.TimeoutException:
            logger.warning("Gemini call timed out after %d ms", self._timeout_ms)
            raise ProviderError("ai_timeout") from None
        except httpx.TransportError as error:
            logger.warning("Gemini network error: %s", type(error).__name__)
            raise ProviderError("ai_network_error") from None
        return ProviderResponse(text=extract_text(response))

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _build_config(self, request: ProviderRequest) -> types.GenerateContentConfig:
        options: dict[str, Any] = {
            "system_instruction": request.system,
            "max_output_tokens": request.max_tokens,
            # Timeout in milliseconds. No retry_options: the SDK then never retries.
            "http_options": types.HttpOptions(timeout=self._timeout_ms),
        }
        if request.response_schema is not None:
            options["response_mime_type"] = "application/json"
            options["response_json_schema"] = to_gemini_schema(request.response_schema)
        if self._thinking_level:
            options["thinking_config"] = types.ThinkingConfig(
                thinking_level=self._thinking_level
            )
        return types.GenerateContentConfig(**options)


def to_gemini_contents(request: ProviderRequest) -> list[types.Content]:
    """Conversation turns as Gemini Content objects (role "user" or "model")."""
    return [
        types.Content(
            role=GEMINI_ROLES[message.role],
            parts=[types.Part.from_text(text=message.content)],
        )
        for message in request.messages
    ]


def to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy a JSON schema keeping only keywords Gemini structured output supports."""
    cleaned: dict[str, Any] = {}
    for key, value in schema.items():
        if key not in SUPPORTED_SCHEMA_KEYWORDS:
            continue
        if key in ("properties", "$defs"):
            # Keys here are property/definition names, not keywords.
            cleaned[key] = {name: to_gemini_schema(sub) for name, sub in value.items()}
        elif key in ("items", "additionalProperties") and isinstance(value, dict):
            cleaned[key] = to_gemini_schema(value)
        elif key in ("anyOf", "oneOf", "prefixItems"):
            cleaned[key] = [to_gemini_schema(sub) for sub in value]
        else:
            cleaned[key] = value
    return cleaned


def map_api_error(error: errors.APIError) -> ProviderError:
    """Turn an SDK HTTP error into a provider error with a safe message."""
    http_code = error.code
    message = (error.message or "").lower()
    if http_code in (401, 403) or (http_code == 400 and "api key" in message):
        return ProviderError("ai_auth_failed")
    if http_code == 404:
        return ProviderError("ai_model_not_found")
    if http_code == 429:
        return ProviderError(
            "ai_quota_exhausted" if is_daily_quota(error) else "ai_rate_limited"
        )
    if http_code in (408, 504):
        return ProviderError("ai_timeout")
    if http_code is not None and http_code >= 500:
        return ProviderError("ai_unavailable")
    return ProviderError("ai_bad_request")


def is_daily_quota(error: errors.APIError) -> bool:
    """Best guess: Google names per-day quotas "...PerDay..." in the error details.

    The official docs do not say how to tell a daily quota from a per-minute
    limit, so anything else is treated as a short-term rate limit.
    """
    return "perday" in str(error.details).lower()


def extract_text(response: types.GenerateContentResponse) -> str:
    """Return the answer text, or raise if it was blocked or empty."""
    feedback = response.prompt_feedback
    if feedback is not None and enum_name(feedback.block_reason) not in (
        None,
        "BLOCKED_REASON_UNSPECIFIED",
    ):
        raise ProviderError("ai_blocked")
    candidate = response.candidates[0] if response.candidates else None
    if candidate is not None and enum_name(candidate.finish_reason) in (
        BLOCKED_FINISH_REASONS
    ):
        raise ProviderError("ai_blocked")
    text = response.text
    if not text or not text.strip():
        raise ProviderError("ai_empty_response")
    # A MAX_TOKENS answer may be cut-off JSON; the harness detects it and repairs once.
    return text


def enum_name(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "name", str(value))
