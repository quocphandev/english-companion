"""Provider-independent AI errors with a user-facing Vietnamese message."""

from app.schemas.error import ErrorBody

# code -> (message_vi, retryable)
PROVIDER_ERRORS: dict[str, tuple[str, bool]] = {
    "ai_auth_failed": (
        "Khóa API của AI bị thiếu hoặc không hợp lệ. Kiểm tra cấu hình rồi khởi động lại app.",
        False,
    ),
    "ai_timeout": ("AI phản hồi quá lâu. Câu của bạn vẫn được giữ, hãy thử lại.", True),
    "ai_rate_limited": (
        "Đang gửi quá nhanh so với giới hạn của AI. Đợi khoảng một phút rồi thử lại.",
        True,
    ),
    "ai_quota_exhausted": (
        "Đã hết hạn mức AI miễn phí hôm nay. Hãy thử lại vào ngày mai.",
        False,
    ),
    "ai_blocked": (
        "AI từ chối trả lời câu này do bộ lọc an toàn. Hãy diễn đạt theo cách khác.",
        False,
    ),
    "ai_empty_response": (
        "AI không trả về nội dung. Câu của bạn vẫn được giữ, hãy thử lại.",
        True,
    ),
    "ai_unavailable": (
        "Dịch vụ AI đang quá tải hoặc gặp lỗi. Câu của bạn vẫn được giữ, hãy thử lại sau.",
        True,
    ),
    "ai_network_error": (
        "Không kết nối được tới dịch vụ AI. Kiểm tra mạng rồi thử lại.",
        True,
    ),
    "ai_model_not_found": (
        "Không tìm thấy model AI đã cấu hình. Kiểm tra tên model trong cấu hình.",
        False,
    ),
    "ai_bad_request": ("Yêu cầu gửi tới AI không hợp lệ.", False),
}


class ProviderError(Exception):
    """An AI call failed. Carries only safe, user-facing information."""

    def __init__(self, code: str) -> None:
        if code not in PROVIDER_ERRORS:
            raise ValueError(f"Unknown provider error code: {code}")
        super().__init__(code)
        self.code = code
        self.message_vi, self.retryable = PROVIDER_ERRORS[code]

    def to_error_body(self) -> ErrorBody:
        return ErrorBody(
            code=self.code, message_vi=self.message_vi, retryable=self.retryable
        )
