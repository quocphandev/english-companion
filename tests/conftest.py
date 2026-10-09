"""Fixtures for every test. Guarantees automated tests never call a real AI API."""

import pytest


@pytest.fixture(autouse=True)
def block_real_gemini_client(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Make creating a real Gemini client fail, except in tests marked live_ai."""
    if request.node.get_closest_marker("live_ai"):
        return

    def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Automated tests must not create a real Gemini client.")

    monkeypatch.setattr("google.genai.Client", refuse)
