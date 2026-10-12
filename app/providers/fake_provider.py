"""Offline provider for development and tests: never calls an external API."""

from pydantic import BaseModel

from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.schemas.ai import Correction, HelpReply, HelpWord, SuggestedWord, TurnReply

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


DEFAULT_FAKE_HELP = HelpReply(
    hint_en="Yesterday I went to ...",
    words=[HelpWord(text="went", meaning_vi="đã đi (quá khứ của go)")],
    explanation_vi="Bắt đầu bằng 'Yesterday I went to' rồi tự hoàn thành câu.",
)

# Canned answer for each output schema, keyed by the schema title.
DEFAULT_FAKE_REPLIES: dict[str, BaseModel] = {
    "TurnReply": DEFAULT_FAKE_REPLY,
    "HelpReply": DEFAULT_FAKE_HELP,
}


class FakeProvider(AIProvider):
    """Returns a fixed, valid answer for whatever schema the request asks for."""

    provider_name = "fake"
    model_name = "fake"

    def __init__(
        self,
        reply: TurnReply = DEFAULT_FAKE_REPLY,
        replies: dict[str, BaseModel] | None = None,
    ) -> None:
        self._replies = {**DEFAULT_FAKE_REPLIES, "TurnReply": reply, **(replies or {})}

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        title = (request.response_schema or {}).get("title", "TurnReply")
        return ProviderResponse(text=self._replies[title].model_dump_json())
