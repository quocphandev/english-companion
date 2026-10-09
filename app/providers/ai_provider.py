"""The AIProvider interface and the request/response types it uses."""

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel


class ProviderMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ProviderRequest(BaseModel):
    """System instructions are kept apart from conversation messages."""

    system: str
    messages: list[ProviderMessage]
    max_tokens: int
    # JSON schema the answer must follow. Providers with structured output use it;
    # the harness validates the answer with Pydantic either way.
    response_schema: dict[str, Any] | None = None


class ProviderResponse(BaseModel):
    """Raw model text; parsing and validation happen in the harness."""

    text: str


class AIProvider(ABC):
    """Contract every AI backend (fake, Gemini) must fulfil.

    Implementations raise app.providers.errors.ProviderError for failures
    (bad key, timeout, rate limit, blocked content, server or network errors).
    """

    @abstractmethod
    def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Send one request and return the model's raw text output."""
