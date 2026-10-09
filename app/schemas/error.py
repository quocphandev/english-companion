from pydantic import BaseModel


class ErrorBody(BaseModel):
    """Error shape returned to the client. Never contains stack traces or secrets."""

    code: str
    message_vi: str
    retryable: bool
