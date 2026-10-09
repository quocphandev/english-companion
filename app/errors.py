"""Application errors and handlers that turn them into {code, message_vi, retryable}."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.conversation import MAX_MESSAGE_CHARS
from app.schemas.error import ErrorBody

logger = logging.getLogger(__name__)


class AppError(Exception):
    """An expected error with a user-facing Vietnamese message."""

    def __init__(
        self, code: str, message_vi: str, *, http_status: int, retryable: bool = False
    ) -> None:
        super().__init__(code)
        self.body = ErrorBody(code=code, message_vi=message_vi, retryable=retryable)
        self.http_status = http_status


def conversation_not_found() -> AppError:
    return AppError(
        "conversation_not_found",
        "Không tìm thấy cuộc trò chuyện.",
        http_status=status.HTTP_404_NOT_FOUND,
    )


def request_id_conflict() -> AppError:
    return AppError(
        "request_id_conflict",
        "Mã yêu cầu này đã được dùng cho một tin nhắn khác.",
        http_status=status.HTTP_409_CONFLICT,
    )


# Validation error types raised by our schemas, mapped to user-facing messages.
VALIDATION_MESSAGES_VI = {
    "empty_message": "Bạn chưa nhập nội dung.",
    "message_too_long": f"Câu quá dài, tối đa {MAX_MESSAGE_CHARS} ký tự.",
}


def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(status_code=exc.http_status, content=exc.body.model_dump())


def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    error_types = [error["type"] for error in exc.errors()]
    code = next(
        (t for t in error_types if t in VALIDATION_MESSAGES_VI), "invalid_input"
    )
    body = ErrorBody(
        code=code,
        message_vi=VALIDATION_MESSAGES_VI.get(code, "Dữ liệu gửi lên không hợp lệ."),
        retryable=False,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=body.model_dump()
    )


def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Log the type only; the stack trace stays on the server, never in the response.
    logger.exception("Unhandled error: %s", type(exc).__name__)
    body = ErrorBody(
        code="internal_error",
        message_vi="Đã có lỗi xảy ra. Vui lòng thử lại.",
        retryable=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body.model_dump()
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
