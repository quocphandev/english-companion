# Progress

## Đang ở mốc
Mốc 1: Khung dự án

## Đã xong
- Khung FastAPI: `app/main.py` với `GET /health` → `{"status": "ok"}`.
- `app/config.py`: `Settings` (pydantic-settings) đọc `.env`, `get_settings()` có cache. `DATABASE_URL` bắt buộc.
- `pyproject.toml`: cấu hình pytest (`pythonpath`, `testpaths`) và ruff isort (`alembic` là thư viện ngoài).
- Tầng dữ liệu (SQLAlchemy sync):
  - `app/db.py`: engine (timezone UTC, `connect_timeout=10`), `SessionLocal`, `get_session()`.
  - `app/models/`: `Profile`, `Conversation`, `Message` với CHECK, FK `ON DELETE CASCADE`, `request_id` unique, `created_at` timestamptz.
- Alembic: `alembic.ini` không chứa URL; `env.py` lấy URL từ Settings. Migration đầu tiên `33b5d3751464` đã áp dụng lên DB dev.
- `docker-compose.yml`: Postgres chỉ mở ở `127.0.0.1:5432`. `.env.example` dùng host `127.0.0.1` (trên Windows, `localhost` thử IPv6 trước nên bị treo).
- CLAUDE.md: quy ước endpoint gọi DB dùng `def` (DB sync).

## Kiểm thử
- `pytest`: 2 passed.
  - `tests/integration/test_health.py`
  - `tests/integration/test_models.py`: tạo profile → conversation → message, đọc lại từ DB; default, UTC, quan hệ đúng.
- `tests/integration/conftest.py`: chạy `alembic upgrade head` trên `TEST_DATABASE_URL`; mỗi test rollback. Sau khi chạy, DB test còn 0 dòng.
- `alembic downgrade base` rồi `upgrade head` trên DB test: chạy được.
- `ruff check .` đạt.
- FR/AC: nền cho FR01 và AC01 (unique `request_id` ở mức DB); AC01 đạt đủ khi có endpoint.

## Bước tiếp theo
1. Fake provider (`app/providers/`) và repository cho conversation/message.
2. Endpoint `POST /api/conversations` và `POST /api/conversations/{id}/messages` (FR01) với fake provider; lịch sử còn sau restart.

## Ý tưởng sau (không làm bây giờ)
- `.venv` đang là Python 3.13.13, còn CLAUDE.md/Dockerfile là 3.12: nên thống nhất một phiên bản.
- Khóa phiên bản dependency (`requirements.lock.txt`) theo yêu cầu bàn giao MVP.
- SPEC mục 8 nói "Foreign key bật trong SQLite" và repositories "ghi đọc SQLite": cập nhật spec sang Postgres.
- `POST /api/conversations` nhận `level`, `correction_mode` nhưng bảng `conversations` không có hai cột này (đang nằm ở `profiles`): cần quyết định khi làm endpoint.
