"""Protection for a public deployment: a shared password and a per-IP rate limit.

Both are off by default (local use). They are turned on by APP_PASSWORD and
RATE_LIMIT_PER_MINUTE, see install_security().
"""

import base64
import binascii
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.schemas.error import ErrorBody

# Paths reachable without the password: Render's health check.
PUBLIC_PATHS = frozenset({"/health"})

# Endpoints that may call the AI; only these count towards the rate limit.
AI_ENDPOINTS = re.compile(r"^/api/(conversations/\d+/(messages|finish)|help|lookup)$")


def password_matches(authorization: str, password: str) -> bool:
    """Check an HTTP Basic header; any user name is accepted, only the password counts."""
    scheme, _, encoded = authorization.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return False
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    _, _, given = decoded.partition(":")
    # compare_digest takes the same time whatever the input, so timing leaks nothing.
    return secrets.compare_digest(given.encode(), password.encode())


class SlidingWindowLimiter:
    """At most `limit` hits per key within the last `window_seconds` (in memory)."""

    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True


def error_response(
    http_status: int, body: ErrorBody, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status, content=body.model_dump(), headers=headers
    )


class SecurityMiddleware:
    """ASGI middleware: password check first, then the AI rate limit."""

    def __init__(
        self,
        app: ASGIApp,
        password: str,
        limiter: SlidingWindowLimiter | None,
    ) -> None:
        self.app = app
        self.password = password
        self.limiter = limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response = self.check(scope)
        if response is not None:
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def check(self, scope: Scope) -> JSONResponse | None:
        path: str = scope["path"]
        if self.password and path not in PUBLIC_PATHS:
            headers = dict(scope["headers"])
            authorization = headers.get(b"authorization", b"").decode("latin-1")
            if not password_matches(authorization, self.password):
                return error_response(
                    status.HTTP_401_UNAUTHORIZED,
                    ErrorBody(
                        code="auth_required",
                        message_vi="Cần mật khẩu để dùng ứng dụng.",
                        retryable=False,
                    ),
                    # Makes the browser show its built-in login box.
                    {
                        "WWW-Authenticate": 'Basic realm="English Companion", charset="UTF-8"'
                    },
                )
        if (
            self.limiter is not None
            and scope["method"] == "POST"
            and AI_ENDPOINTS.match(path)
        ):
            client = scope.get("client")
            key = client[0] if client else "unknown"
            if not self.limiter.allow(key):
                return error_response(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    ErrorBody(
                        code="rate_limited",
                        message_vi="Bạn gửi quá nhanh. Hãy đợi một phút rồi thử lại.",
                        retryable=True,
                    ),
                    {"Retry-After": "60"},
                )
        return None


def install_security(app: FastAPI, settings: Settings) -> None:
    """Add the middleware only when a password or a rate limit is configured."""
    password = settings.app_password.get_secret_value()
    limit = settings.rate_limit_per_minute
    if not password and limit == 0:
        return
    limiter = SlidingWindowLimiter(limit) if limit > 0 else None
    app.add_middleware(SecurityMiddleware, password=password, limiter=limiter)
