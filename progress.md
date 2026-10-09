# Progress

## Đang ở mốc
Mốc 1: Khung dự án

## Đã xong
- Khung FastAPI: `app/main.py` với `GET /health` → `{"status": "ok"}`.
- `app/config.py`: `Settings` (pydantic-settings) đọc `.env`, `get_settings()` có cache. Chưa nối DB.
- `pyproject.toml`: cấu hình pytest (`pythonpath`, `testpaths`).

## Kiểm thử
- `tests/integration/test_health.py`: `/health` trả 200 và đúng body. `pytest` đạt (1 passed), `ruff check` và `ruff format --check` đạt.
- Chạy thật bằng uvicorn trên 127.0.0.1:8000: `/health` và `/docs` trả 200. Settings đọc `.env` đúng (`ai_provider=fake`).

## Bước tiếp theo
1. Kết nối Postgres: SQLAlchemy engine/session, đổi `database_url` thành bắt buộc, khởi tạo Alembic.
2. Fake provider và chat giả lập (FR01), lịch sử còn sau restart.

## Ý tưởng sau (không làm bây giờ)
- `.venv` đang là Python 3.13.13, còn CLAUDE.md/Dockerfile là 3.12: nên thống nhất một phiên bản.
- Khóa phiên bản dependency (`requirements.lock.txt`) theo yêu cầu bàn giao MVP.
