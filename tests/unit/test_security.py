"""Shared password, AI rate limit and deployment settings (public demo)."""

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.security import SlidingWindowLimiter, install_security, password_matches

DB_URL = "postgresql+psycopg://u:p@127.0.0.1:5432/db"


def make_settings(**overrides: object) -> Settings:
    # _env_file=None: never read the developer's real .env in unit tests.
    values = {"database_url": DB_URL, **overrides}
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


def basic(password: str, user: str = "friend") -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def make_app(**overrides: object) -> TestClient:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/vocabulary")
    def page() -> dict[str, str]:
        return {"page": "vocabulary"}

    @app.post("/api/help")
    def ai_endpoint() -> dict[str, str]:
        return {"hint": "..."}

    @app.post("/api/vocabulary")
    def save_word() -> dict[str, str]:
        return {"saved": "yes"}

    install_security(app, make_settings(**overrides))
    return TestClient(app)


def test_password_matches_only_the_right_basic_header() -> None:
    assert password_matches(basic("s3cret")["Authorization"], "s3cret")
    assert password_matches(basic("mật khẩu", user="")["Authorization"], "mật khẩu")
    assert not password_matches(basic("wrong")["Authorization"], "s3cret")
    assert not password_matches("Bearer s3cret", "s3cret")
    assert not password_matches("Basic not-base64!", "s3cret")
    assert not password_matches("", "s3cret")


def test_pages_need_the_password_but_health_does_not() -> None:
    client = make_app(app_password="s3cret")

    denied = client.get("/vocabulary")
    wrong = client.get("/vocabulary", headers=basic("nope"))
    allowed = client.get("/vocabulary", headers=basic("s3cret"))

    assert denied.status_code == 401
    assert denied.headers["WWW-Authenticate"].startswith("Basic")
    assert denied.json()["code"] == "auth_required"
    assert wrong.status_code == 401
    assert allowed.status_code == 200
    assert client.get("/health").status_code == 200


def test_no_password_and_no_limit_leaves_the_app_open() -> None:
    client = make_app()

    assert client.get("/vocabulary").status_code == 200
    assert all(client.post("/api/help").status_code == 200 for _ in range(20))


def test_ai_endpoints_are_rate_limited_per_client() -> None:
    client = make_app(rate_limit_per_minute=2)

    codes = [client.post("/api/help").status_code for _ in range(3)]
    blocked = client.post("/api/help")

    assert codes == [200, 200, 429]
    assert blocked.json() == {
        "code": "rate_limited",
        "message_vi": "Bạn gửi quá nhanh. Hãy đợi một phút rồi thử lại.",
        "retryable": True,
    }
    # Endpoints that never call the AI are not limited.
    assert client.post("/api/vocabulary").status_code == 200


def test_limiter_forgets_hits_older_than_the_window() -> None:
    now = [0.0]
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    now[0] = 60.0
    assert limiter.allow("a")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:p@host/db?sslmode=require",
            "postgresql+psycopg://u:p@host/db?sslmode=require",
        ),
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        (DB_URL, DB_URL),
    ],
)
def test_database_url_uses_the_psycopg_driver(given: str, expected: str) -> None:
    assert make_settings(database_url=given).database_url == expected


def test_public_demo_refuses_to_start_without_a_password() -> None:
    with pytest.raises(ValidationError, match="APP_PASSWORD"):
        make_settings(public_demo=True)

    assert make_settings(public_demo=True, app_password="s3cret").public_demo
