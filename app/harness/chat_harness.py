"""Run one chat turn: build context, call the provider, validate, repair once."""

import logging
import time
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.harness.context import TurnContext, build_request
from app.harness.prompts import REPAIR_INSTRUCTION_TEMPLATE
from app.providers.ai_provider import AIProvider, ProviderMessage, ProviderRequest
from app.providers.errors import ProviderError
from app.schemas.ai import TurnReply
from app.schemas.error import ErrorBody

logger = logging.getLogger(__name__)

# One normal call plus at most one repair call per turn.
MAX_CALLS_PER_TURN = 2

INVALID_AI_OUTPUT_ERROR = ErrorBody(
    code="invalid_ai_output",
    message_vi="AI trả về dữ liệu không hợp lệ. Câu của bạn vẫn được giữ, hãy thử lại.",
    retryable=True,
)


class TurnResult(BaseModel):
    """Outcome of a turn. Never carries the raw (possibly invalid) model text."""

    status: Literal["succeeded", "failed"]
    reply: TurnReply | None = None
    attempts: int
    error: ErrorBody | None = None
    duration_ms: int = 0


class ChatHarness:
    def __init__(self, provider: AIProvider, max_output_tokens: int) -> None:
        self._provider = provider
        self._max_output_tokens = max_output_tokens

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def run_turn(self, context: TurnContext) -> TurnResult:
        started = time.perf_counter()
        request = build_request(context, self._max_output_tokens)

        for attempt in range(1, MAX_CALLS_PER_TURN + 1):
            try:
                raw_text = self._provider.complete(request).text
            except ProviderError as error:
                # Provider failures (timeout, rate limit, bad key...) are never retried here.
                result = TurnResult(
                    status="failed", attempts=attempt, error=error.to_error_body()
                )
                return finish_turn(result, started)
            try:
                reply = TurnReply.model_validate_json(raw_text)
            except ValidationError as error:
                logger.warning(
                    "Invalid AI output: attempt=%d error_count=%d",
                    attempt,
                    error.error_count(),
                )
                request = add_repair_messages(request, raw_text, error)
                continue
            result = TurnResult(status="succeeded", reply=reply, attempts=attempt)
            return finish_turn(result, started)

        result = TurnResult(
            status="failed",
            attempts=MAX_CALLS_PER_TURN,
            error=INVALID_AI_OUTPUT_ERROR,
        )
        return finish_turn(result, started)


def format_validation_errors(error: ValidationError) -> str:
    """List problems as "field: message", without echoing the invalid input."""
    lines = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "(root)"
        lines.append(f"- {location}: {item['msg']}")
    return "\n".join(lines)


def add_repair_messages(
    request: ProviderRequest, raw_text: str, error: ValidationError
) -> ProviderRequest:
    """Append the invalid answer and an instruction to fix it."""
    repair = REPAIR_INSTRUCTION_TEMPLATE.format(errors=format_validation_errors(error))
    return request.model_copy(
        update={
            "messages": [
                *request.messages,
                ProviderMessage(role="assistant", content=raw_text or "(empty)"),
                ProviderMessage(role="user", content=repair),
            ]
        }
    )


def finish_turn(result: TurnResult, started: float) -> TurnResult:
    """Record the duration and log metadata only, never conversation content."""
    result.duration_ms = duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "Chat turn finished: status=%s attempts=%d error=%s duration_ms=%d",
        result.status,
        result.attempts,
        result.error.code if result.error else "-",
        duration_ms,
    )
    return result
