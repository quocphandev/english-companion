# Sổ tay học: giải thích từng việc đã làm

Mỗi việc xong có một file. Đọc theo thứ tự số; mỗi file chỉ giải thích khái niệm mới xuất hiện ở bước đó.

| # | File | Nội dung | Mốc |
|---|---|---|---|
| 01 | [01-fastapi-skeleton.md](01-fastapi-skeleton.md) | Khung FastAPI, `/health`, đọc cấu hình `.env`, test đầu tiên | 1 |
| 02 | [02-database-alembic.md](02-database-alembic.md) | Model SQLAlchemy, engine/session, Alembic migration, test với DB thật | 1 |
| 03 | [03-provider-harness.md](03-provider-harness.md) | Interface AIProvider, FakeProvider, schema Pydantic, harness sửa JSON | 1 |
| 04 | [04-conversation-api.md](04-conversation-api.md) | API hội thoại: router/service/repository, 2 transaction, idempotency, lỗi có cấu trúc | 1 |
| 05 | [05-chat-ui.md](05-chat-ui.md) | Trang chat: Jinja2 render phía server, `fetch`, chống XSS, CSP | 1 |
| 06 | [06-read-aloud.md](06-read-aloud.md) | Đọc hội thoại bằng `speechSynthesis`, tạm dừng/trước/sau/tốc độ (FR09) | 2 |
| 07 | [07-gemini-provider.md](07-gemini-provider.md) | GeminiProvider, lỗi có cấu trúc, hạn mức ngày `ai_runs` | 2 |
| 08 | [08-corrections-eval.md](08-corrections-eval.md) | Prompt v2, thẻ sửa hai chế độ, bộ 30 câu đánh giá | 2 |
| 09 | [09-help-when-stuck.md](09-help-when-stuck.md) | "Giúp tôi" 3 mức + ý tiếng Việt, harness tổng quát | 2 |
| 10 | [10-opening-question.md](10-opening-question.md) | Chatbot mở đầu bằng câu hỏi (FR01) | 2 |
| 11 | [11-word-lookup.md](11-word-lookup.md) | Bấm từ, chọn cụm, tra nghĩa theo ngữ cảnh, cache (FR05) | 3 |
| 12 | [12-vocabulary.md](12-vocabulary.md) | Lưu từ không trùng, trang Từ vựng (FR06) | 3 |
| 13 | [13-flashcard-review.md](13-flashcard-review.md) | Flashcard Nhớ/Chưa nhớ, lọc chưa ôn/đã ôn (FR07 MVP) | 4 |
| 14 | [14-session-summary.md](14-session-summary.md) | Kết thúc buổi, tổng kết không bịa (FR10) | 4 |

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
| Jinja2: `{{ }}`, `extends`/`block`, `macro` | Render HTML phía server, tự escape | 05 |
| `fetch`, `async`/`await` (JS) | Gửi HTTP không tải lại trang | 05 |
| XSS, `textContent`, CSP | Ba lớp chống chèn script | 05 |
| `selectinload`, vấn đề N+1 | Tải dữ liệu liên quan bằng 1 truy vấn | 05 |
| `<dialog>` | Hộp thoại có sẵn của HTML | 05 |
| `generate_content`, structured output | Gọi Gemini không trạng thái, ép JSON theo schema | 07 |
| phân loại lỗi provider, retryable | Mỗi loại lỗi một phản ứng | 07 |
| `timezone()` trong Postgres | Đếm "hôm nay" theo múi giờ | 07 |
| prompt injection | Câu người dùng cố điều khiển AI | 08 |
| bộ câu đánh giá cố định | Đo chất lượng AI thay cho so khớp | 08 |
| data migration | Migration kèm chép/sửa dữ liệu cũ | 08 |
| `<details>`/`<summary>` | Thu gọn/mở rộng không cần JS | 08 |
| harness tổng quát `run_structured` | Một vòng lặp gọi–kiểm tra–sửa cho mọi schema | 09 |
| `speechSynthesis`, `SpeechSynthesisUtterance` | Đọc chữ thành tiếng trong trình duyệt | 06 |
| `Cache-Control: no-cache` | Trình duyệt luôn kiểm tra lại file tĩnh | 06 |
| code point vs UTF-16 | Cách Python và JS đếm vị trí ký tự | 11 |
| cache theo ngữ cảnh, `ON CONFLICT DO NOTHING` | Tái dùng kết quả tra chỉ khi cùng câu và vùng chọn | 11 |
| chuẩn hóa khóa, unique nhiều cột | Phát hiện trùng ở mức DB | 12 |
| `<dialog method="dialog">` | Hộp xác nhận không cần `confirm()` | 12 |
| kế thừa template nhiều tầng | Khung trang dùng chung | 12 |
| window function `row_number() OVER` | Lấy dòng mới nhất của mỗi nhóm | 13 |
| `CASE`, `EXISTS` | Sắp xếp theo nhóm, lọc theo bảng khác | 13 |
| JSONB cho dữ liệu bán cấu trúc | Lưu chi tiết chỉ để hiển thị | 14 |
