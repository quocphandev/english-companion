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
- AI (chưa gọi Claude thật):
  - `app/schemas/ai.py`: `TurnReply` (`reply_en`, tối đa 3 `corrections`, tối đa 3 `suggested_words`).
  - `app/providers/`: interface `AIProvider` (ABC, sync) và `FakeProvider` trả JSON cố định.
  - `app/harness/`: `build_request` (system prompt tách khỏi messages, 20 tin gần nhất, tin đầu là user); `ChatHarness.run_turn` validate bằng Pydantic, JSON sai thì sửa 1 lần (tối đa 2 call), vẫn sai thì `failed`/`invalid_ai_output`, không trả JSON thô. Log chỉ ghi metadata.

## Kiểm thử
- `pytest`: 17 passed.
  - `tests/unit/test_ai_schemas.py`: validator nhận JSON đúng, từ chối thiếu/rỗng `reply_en`, >3 corrections, category lạ, chuỗi không phải JSON.
  - `tests/unit/test_context.py`: giữ 20 tin, tin đầu là user, câu người dùng không nằm trong system prompt.
  - `tests/unit/test_chat_harness.py`: thành công 1 call; JSON hỏng → sửa thành công ở call 2; sai schema → sửa; hỏng 2 lần → `failed`, đúng 2 call.
  - `tests/integration/test_health.py`
  - `tests/integration/test_models.py`: tạo profile → conversation → message, đọc lại từ DB; default, UTC, quan hệ đúng.
- `tests/integration/conftest.py`: chạy `alembic upgrade head` trên `TEST_DATABASE_URL`; mỗi test rollback. Sau khi chạy, DB test còn 0 dòng.
- `alembic downgrade base` rồi `upgrade head` trên DB test: chạy được.
- `ruff check .` đạt.
- Chạy thật `ChatHarness(FakeProvider())`: `succeeded`, 1 lần gọi, reply có cấu trúc đúng.
- FR/AC: nền cho FR01 và AC01 (unique `request_id` ở mức DB); AC01 đạt đủ khi có endpoint. AC08 phần "JSON lỗi chỉ sửa một lần" đạt ở mức harness; phần timeout/key sai làm ở Mốc 2.

## Bước tiếp theo
1. Repository cho conversation/message và `conversation_service` (lưu lượt pending → harness → ghi reply trong một transaction).
2. Endpoint `POST /api/conversations` và `POST /api/conversations/{id}/messages` (FR01) với fake provider; lịch sử còn sau restart.

## Ý tưởng sau (không làm bây giờ)
- `.venv` đang là Python 3.13.13, còn CLAUDE.md/Dockerfile là 3.12: nên thống nhất một phiên bản.
- Khóa phiên bản dependency (`requirements.lock.txt`) theo yêu cầu bàn giao MVP.
- SPEC mục 8 nói "Foreign key bật trong SQLite" và repositories "ghi đọc SQLite": cập nhật spec sang Postgres.
- `POST /api/conversations` nhận `level`, `correction_mode` nhưng bảng `conversations` không có hai cột này (đang nằm ở `profiles`): cần quyết định khi làm endpoint.
- Harness Mốc 2: bóc khối ```json khi Claude bọc ngoài; giới hạn context theo token; xử lý lỗi provider (timeout, key sai) thành lỗi `{code, message_vi, retryable}`; factory chọn provider theo `AI_PROVIDER`.
- Lưu `PROMPT_VERSION` (`app/harness/prompts.py`) vào bảng `corrections`/`ai_runs` khi tạo các bảng này.
- Console Windows mặc định cp1252 nên `print` chữ tiếng Việt bị lỗi: đặt `PYTHONIOENCODING=utf-8` khi chạy script thử.
