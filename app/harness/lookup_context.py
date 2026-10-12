"""Build the provider request for a contextual lookup (FR05)."""

import hashlib
import json

from pydantic import BaseModel

from app.harness.prompts import LOOKUP_PROMPT_VERSION, LOOKUP_SYSTEM_PROMPT
from app.providers.ai_provider import ProviderMessage, ProviderRequest
from app.schemas.ai import LookupReply

TARGET_LANGUAGE = "vi"


class LookupContext(BaseModel):
    """The sentence and the selection inside it (offsets relative to the sentence)."""

    sentence: str
    start: int
    end: int

    @property
    def selected_text(self) -> str:
        return self.sentence[self.start : self.end]

    def marked_sentence(self) -> str:
        """The sentence with the selection wrapped in ⟦ ⟧."""
        s = self.sentence
        return f"{s[: self.start]}⟦{s[self.start : self.end]}⟧{s[self.end :]}"


def lookup_cache_key(context: LookupContext) -> str:
    """Same sentence + same selection + same language + same prompt => same key."""
    parts = [
        LOOKUP_PROMPT_VERSION,
        TARGET_LANGUAGE,
        context.sentence,
        context.start,
        context.end,
    ]
    payload = json.dumps(parts, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_lookup_request(context: LookupContext, max_tokens: int) -> ProviderRequest:
    system = LOOKUP_SYSTEM_PROMPT.format(
        schema=json.dumps(LookupReply.model_json_schema(), indent=2)
    )
    # The sentence is conversation content: it goes in the user turn, never in system.
    ask = (
        f"Sentence: <sentence>{context.marked_sentence()}</sentence>\n"
        f"Selected: <selection>{context.selected_text}</selection>"
    )
    return ProviderRequest(
        system=system,
        messages=[ProviderMessage(role="user", content=ask)],
        max_tokens=max_tokens,
        response_schema=LookupReply.model_json_schema(),
    )
