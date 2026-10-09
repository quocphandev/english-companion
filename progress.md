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
- API hội thoại (FR01) với fake provider:
  - `POST /api/conversations` (topic, level, correction_mode → `conversation_id`); level/mode ghi đè vào profile mặc định (get-or-create).
  - `POST /api/conversations/{id}/messages`: tx1 lưu câu user `pending` → harness (không giữ transaction) → tx2 lưu reply + corrections + đổi status. AI lỗi → `200` + `status: failed` + `error` retryable, câu user vẫn còn.
  - Idempotency theo `request_id`: đã xong thì trả kết quả cũ (không gọi AI), `pending` thì trả pending, `failed` thì thử lại trên cùng câu; trùng đồng thời được UNIQUE chặn và xử lý; khác nội dung → 409.
  - Kiến trúc: `routers/` → `services/` → `repositories/` + `harness/`; `dependencies.py` (DI); `errors.py` (mọi lỗi dạng `{code, message_vi, retryable}`).
  - Migration `9ba16f575a07`: bảng `corrections` (có `prompt_version`), cột `messages.reply_to_message_id` (UNIQUE). Đã áp dụng lên DB dev.
- Quy tắc mới: mỗi việc có file giải thích trong `docs/learning/` (01–04 đã có).

## Kiểm thử
- `pytest`: 34 passed.
  - `tests/unit/test_ai_schemas.py`: validator nhận JSON đúng, từ chối thiếu/rỗng `reply_en`, >3 corrections, category lạ, chuỗi không phải JSON.
  - `tests/unit/test_context.py`: giữ 20 tin, tin đầu là user, câu người dùng không nằm trong system prompt.
  - `tests/unit/test_chat_harness.py`: thành công 1 call; JSON hỏng → sửa thành công ở call 2; sai schema → sửa; hỏng 2 lần → `failed`, đúng 2 call.
  - `tests/integration/test_health.py`
  - `tests/integration/test_models.py`: tạo profile → conversation → message, đọc lại từ DB; default, UTC, quan hệ đúng.
  - `tests/integration/test_conversations_api.py` (19 test): tạo hội thoại/profile; lỗi 422 đúng format; lưu reply + corrections + `prompt_version`; giữ nguyên văn câu; context chỉ của hội thoại hiện tại; AC01 (rỗng, khoảng trắng, 2.001 ký tự bị chặn; 2.000 được nhận; gửi trùng `request_id` → 1 lượt, 1 lần gọi AI; trùng đồng thời qua UNIQUE); 409; 404; AI lỗi → `failed`, câu còn trong DB; thử lại dùng lại cùng câu.
- `tests/integration/conftest.py`: chạy `alembic upgrade head` trên `TEST_DATABASE_URL`; mỗi test rollback. Sau khi chạy, DB test còn 0 dòng.
- `alembic downgrade base` rồi `upgrade head` trên DB test: chạy được.
- `ruff check .` đạt.
- Chạy thật `ChatHarness(FakeProvider())`: `succeeded`, 1 lần gọi, reply có cấu trúc đúng.
- Chạy thật uvicorn + DB dev: tạo hội thoại, gửi câu (succeeded, có correction), gửi lại cùng id (vẫn 1 câu user + 1 reply trong DB), câu rỗng → `empty_message`, id lạ → 404.
- FR/AC: **AC01 đạt** (test AC01 ở trên). FR01 đạt phần gửi/nhận, giữ câu gốc, trạng thái, lịch sử theo hội thoại; còn thiếu câu hỏi mở đầu. AC08: JSON lỗi chỉ sửa một lần, AI lỗi không mất câu nhập (với fake provider); timeout/key sai thật làm ở Mốc 2.

## Bước tiếp theo
1. API đọc lịch sử: `GET /api/conversations` và `GET /api/conversations/{id}/messages` (mở lại sau restart).
2. Giao diện chat Jinja2 + JS nhỏ (gửi, trạng thái đang xử lý/thành công/lỗi, thử lại cùng `request_id`) để hoàn tất Mốc 1.

## Ý tưởng sau (không làm bây giờ)
- `.venv` đang là Python 3.13.13, còn CLAUDE.md/Dockerfile là 3.12: nên thống nhất một phiên bản.
- Khóa phiên bản dependency (`requirements.lock.txt`) theo yêu cầu bàn giao MVP.
- SPEC mục 8 nói "Foreign key bật trong SQLite" và repositories "ghi đọc SQLite": cập nhật spec sang Postgres.
- Đã chọn ghi level/mode vào profile: hội thoại cũ sẽ dùng cài đặt mới nhất. Nếu sau này cần mỗi hội thoại giữ cài đặt riêng thì thêm cột vào `conversations`.
- FR01: chatbot mở đầu bằng một câu hỏi ngắn khi tạo hội thoại.
- Lượt `pending` bị kẹt nếu server sập giữa lúc gọi AI: coi `pending` quá 65 giây là `failed` để thử lại được.
- Lưu `suggested_words` (hiện chỉ có trong output AI, chưa lưu và chưa trả qua API).
- Đưa giới hạn 2.000 ký tự (`MAX_MESSAGE_CHARS`) vào `Settings`.
- AC04: ẩn thẻ lỗi ngay ở chế độ giao tiếp (phần UI).
- Harness Mốc 2: bóc khối ```json khi Claude bọc ngoài; giới hạn context theo token; xử lý lỗi provider (timeout, key sai) thành lỗi `{code, message_vi, retryable}`; factory chọn provider theo `AI_PROVIDER`.
- Lưu `PROMPT_VERSION` vào bảng `ai_runs` khi tạo bảng này (đã lưu ở `corrections`).
- Console Windows mặc định cp1252 nên `print` chữ tiếng Việt bị lỗi: đặt `PYTHONIOENCODING=utf-8` khi chạy script thử.
