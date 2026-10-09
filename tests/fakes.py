"""Test doubles shared by unit and integration tests."""

from app.providers.ai_provider import AIProvider, ProviderRequest, ProviderResponse
from app.providers.errors import ProviderError
from app.providers.fake_provider import FakeProvider


class ScriptedProvider(AIProvider):
    """Returns (or raises) the given outputs in order and records every request."""

    def __init__(self, outputs: list[str | Exception]) -> None:
        self._outputs = list(outputs)
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        output = self._outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return ProviderResponse(text=output)


class RecordingFakeProvider(FakeProvider):
    """FakeProvider that also records every request, to count AI calls."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        return super().complete(request)


class FailingProvider(AIProvider):
    """Always fails with the given provider error code, counting calls."""

    def __init__(self, error_code: str) -> None:
        self._error_code = error_code
        self.calls = 0

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        raise ProviderError(self._error_code)
