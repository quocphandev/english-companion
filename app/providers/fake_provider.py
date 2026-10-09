"""Offline provider for development and tests: never calls an external API."""

from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.schemas.ai import Correction, SuggestedWord, TurnReply

DEFAULT_FAKE_REPLY = TurnReply(
    reply_en="That sounds nice! What did you do after that?",
    corrections=[
        Correction(
            category="grammar",
            original_span="I go",
            corrected_text="I went",
            explanation_vi="Dùng quá khứ đơn (went) vì hành động đã xảy ra hôm qua.",
        )
    ],
    suggested_words=[
        SuggestedWord(
            text="commute", meaning_vi="đi lại hằng ngày giữa nhà và nơi làm việc"
        )
    ],
)


class FakeProvider(AIProvider):
    """Always returns the same valid JSON reply."""

    provider_name = "fake"
    model_name = "fake"

    def __init__(self, reply: TurnReply = DEFAULT_FAKE_REPLY) -> None:
        self._reply = reply

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(text=self._reply.model_dump_json())
