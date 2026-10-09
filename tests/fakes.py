"""Test doubles shared by unit and integration tests."""

from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.providers.fake_provider import FakeProvider


class ScriptedProvider(AIProvider):
    """Returns the given outputs in order and records every request."""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(text=self._outputs.pop(0))


class RecordingFakeProvider(FakeProvider):
    """FakeProvider that also records every request, to count AI calls."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return super().complete(request)
