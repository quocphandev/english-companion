# Sổ tay học: giải thích từng việc đã làm

Mỗi việc xong có một file. Đọc theo thứ tự số; mỗi file chỉ giải thích khái niệm mới xuất hiện ở bước đó.

| # | File | Nội dung | Mốc |
|---|---|---|---|
| 01 | [01-fastapi-skeleton.md](01-fastapi-skeleton.md) | Khung FastAPI, `/health`, đọc cấu hình `.env`, test đầu tiên | 1 |
| 02 | [02-database-alembic.md](02-database-alembic.md) | Model SQLAlchemy, engine/session, Alembic migration, test với DB thật | 1 |
| 03 | [03-provider-harness.md](03-provider-harness.md) | Interface AIProvider, FakeProvider, schema Pydantic, harness sửa JSON | 1 |
| 04 | [04-conversation-api.md](04-conversation-api.md) | API hội thoại: router/service/repository, 2 transaction, idempotency, lỗi có cấu trúc | 1 |

## Từ điển nhanh (khái niệm và file giải thích lần đầu)

| Khái niệm | Ý nghĩa ngắn | Xem |
|---|---|---|
| package, `__init__.py` | Thư mục Python import được | 01 |
| venv | Môi trường Python riêng của dự án | 01 |
| decorator (`@app.get`, `@lru_cache`) | Hàm "bọc" thêm hành vi cho hàm khác | 01 |
| pydantic-settings | Đọc biến môi trường thành object có kiểu | 01 |
| TestClient | Gọi API trong bộ nhớ, không cần bật server | 01 |
| model, `Mapped[...]` | Class Python mô tả một bảng | 02 |
| engine, session, transaction | Kết nối, phiên làm việc, nhóm thay đổi "tất cả hoặc không" | 02 |
| migration (Alembic) | File mô tả một bước đổi schema, có upgrade/downgrade | 02 |
| fixture (pytest) | Hàm chuẩn bị dữ liệu/tài nguyên cho test | 02 |
| savepoint, rollback | Cách mỗi test tự dọn dữ liệu | 02 |
| interface (ABC) | Hợp đồng method mà class phải có | 03 |
| validation | Kiểm tra dữ liệu theo schema trước khi dùng | 03 |
| dependency injection | Truyền phụ thuộc từ ngoài vào thay vì tự tạo | 03 |
| `pytest.mark.parametrize` | Chạy một test với nhiều bộ dữ liệu | 03 |
| kiến trúc router → service → repository | Mỗi tầng một việc, phụ thuộc một chiều | 04 |
| transaction ngắn quanh lời gọi AI | Không giữ transaction khi chờ AI | 04 |
| idempotency, `request_id` | Gửi lặp vẫn chỉ một kết quả | 04 |
| `Depends`, `Annotated`, `dependency_overrides` | DI của FastAPI và cách thay trong test | 04 |
| exception handler | Đổi mọi lỗi sang `{code, message_vi, retryable}` | 04 |
| `PydanticCustomError` | Validator tự đặt mã lỗi | 04 |
| `monkeypatch` (pytest) | Tạm thay hàm trong một test | 04 |
