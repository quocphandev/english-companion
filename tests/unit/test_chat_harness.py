from app.harness.chat_harness import ChatHarness
from app.harness.context import TurnContext
from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.providers.fake_provider import DEFAULT_FAKE_REPLY, FakeProvider

VALID_JSON = '{"reply_en": "Great! What did you do next?", "corrections": []}'


class ScriptedProvider(AIProvider):
    """Returns the given outputs in order and records every request."""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(text=self._outputs.pop(0))


def make_context() -> TurnContext:
    return TurnContext(
        level="A2",
        correction_mode="learning",
        topic="work",
        user_text="Yesterday I go to work.",
    )


def test_fake_provider_turn_succeeds_in_one_call() -> None:
    harness = ChatHarness(provider=FakeProvider(), max_output_tokens=800)

    result = harness.run_turn(make_context())

    assert result.status == "succeeded"
    assert result.attempts == 1
    assert result.reply == DEFAULT_FAKE_REPLY


def test_invalid_json_is_repaired_with_one_extra_call() -> None:
    provider = ScriptedProvider(["this is not json", VALID_JSON])
    harness = ChatHarness(provider=provider, max_output_tokens=800)

    result = harness.run_turn(make_context())

    assert result.status == "succeeded"
    assert result.attempts == 2
    assert result.reply is not None
    assert result.reply.reply_en == "Great! What did you do next?"
    assert len(provider.requests) == 2
    repair_request = provider.requests[1]
    assert repair_request.system == provider.requests[0].system
    assert repair_request.messages[-2].role == "assistant"
    assert repair_request.messages[-2].content == "this is not json"
    assert repair_request.messages[-1].role == "user"
    assert "not valid" in repair_request.messages[-1].content


def test_schema_violation_triggers_repair() -> None:
    provider = ScriptedProvider(['{"corrections": []}', VALID_JSON])
    harness = ChatHarness(provider=provider, max_output_tokens=800)

    result = harness.run_turn(make_context())

    assert result.status == "succeeded"
    assert result.attempts == 2
    assert "reply_en" in provider.requests[1].messages[-1].content


def test_still_invalid_after_repair_fails_without_third_call() -> None:
    provider = ScriptedProvider(["not json", '{"still broken'])
    harness = ChatHarness(provider=provider, max_output_tokens=800)

    result = harness.run_turn(make_context())

    assert result.status == "failed"
    assert result.error_code == "invalid_ai_output"
    assert result.reply is None
    assert result.attempts == 2
    assert len(provider.requests) == 2
    assert "still broken" not in result.model_dump_json()
