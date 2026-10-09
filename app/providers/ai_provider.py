"""The AIProvider interface and the request/response types it uses."""

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class ProviderMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ProviderRequest(BaseModel):
    """System instructions are kept apart from conversation messages."""

    system: str
    messages: list[ProviderMessage]
    max_tokens: int


class ProviderResponse(BaseModel):
    """Raw model text; parsing and validation happen in the harness."""

    text: str


class AIProvider(ABC):
    """Contract every AI backend (fake, Claude) must fulfil."""

    @abstractmethod
    def complete(self, request: ProviderRequest) -> ProviderResponse:
        """Send one request and return the model's raw text output."""
