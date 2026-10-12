# Progress

## Đang ở mốc
Mốc 2: Gemini và sửa lỗi (Mốc 1 đã xong).

## Đã xong

### Mốc 1: khung dự án (PR #1–#6)
- FastAPI, `Settings` đọc `.env`, Postgres 17 (Docker, chỉ mở `127.0.0.1:5432`), SQLAlchemy sync, Alembic.
- Bảng `profiles`, `conversations`, `messages`, `corrections` (có `prompt_version`), `messages.reply_to_message_id`.
- API `POST /api/conversations` và `POST /api/conversations/{id}/messages`.
  - Ghi trong 2 transaction ngắn quanh lời gọi AI.
  - Idempotency theo `request_id`.
  - Lỗi trả dạng `{code, message_vi, retryable}`.
- Harness: context 20 tin, system prompt tách riêng, validate Pydantic, sửa JSON 1 lần (tối đa 2 call).
- Trang chat Jinja2 + JS thuần: thanh bên, tạo hoặc mở hội thoại, trạng thái gửi, giữ câu khi lỗi, lịch sử còn sau restart.
- Chống XSS 3 lớp: autoescape, JS chỉ dùng `textContent`, CSP.

### Mốc 2 (đang làm)
- **Gemini (PR #8):**
  - `GeminiProvider` dùng gói `google-genai` 2.29, gọi `models.generate_content`.
  - System instruction, structured output theo schema `TurnReply` (đã lọc các từ khóa Gemini không hỗ trợ), timeout 30 s, không retry, `thinking_level` lấy từ cấu hình.
  - Lỗi được đổi thành 10 mã `ai_*`, không lộ key hay nội dung lỗi gốc.
  - Chọn provider bằng `AI_PROVIDER` (`fake` mặc định, hoặc `gemini`).
  - `tests/conftest.py` chặn mọi lần tạo client Gemini thật trong test.
- **Hạn mức ngày (PR #10):**
  - Bảng `ai_runs` (chỉ metadata, migration `2ee8aebf5926`), mỗi lượt chat ghi một dòng trong tx2.
  - Chặn lượt mới và lượt thử lại khi đã dùng đủ `DAILY_AI_LIMIT` lần gọi trong ngày (tính theo giờ profile) → 429 `daily_limit_reached`.
  - Provider `fake` không bị đếm.
- **Đọc hội thoại (một phần FR09, ngoại lệ đã duyệt; PR #7, #9):**
  - Đọc lần lượt cả hội thoại bằng `speechSynthesis`, tách câu, chọn giọng Anh/Việt theo từng câu.
  - Tô nổi bật và tự cuộn tới tin đang đọc; chọn "Cả hai bên" hoặc "Chỉ chatbot"; nút Dừng.
  - Tự dừng khi gửi tin hoặc rời trang.
  - Giao diện responsive: menu ☰ trên điện thoại.

## Kiểm thử
- `pytest`: 89 passed, 3 skipped (smoke test live). `node --test "tests/js/**/*.test.mjs"`: 28 passed. `ruff check .` đạt.
- Smoke test Gemini thật (`RUN_LIVE_AI=1`, 3 lần gọi), đạt 3/3:
  - JSON đúng schema.
  - Sửa `go → went`.
  - Câu đúng không bị gắn lỗi.
  - Key sai trả `400 INVALID_ARGUMENT`, được đổi thành `ai_auth_failed`.
- AC đã đạt:
  - **AC01**: `tests/integration/test_conversations_api.py` (các test chặn câu rỗng hoặc quá dài, gửi trùng `request_id`, gửi đồng thời).
  - **AC08**, phần đã làm: JSON lỗi chỉ sửa 1 lần (`test_chat_harness.py`); AI lỗi không mất câu nhập (`test_invalid_ai_output_marks_turn_failed_and_keeps_text`, `test_provider_error_returns_structured_error_and_keeps_text`).

## FR02, sửa lỗi hai chế độ — xong (merge từ `feat/FR02-correction-modes`)
- Cài đặt `level` / `correction_mode` lưu theo từng hội thoại (migration `7060bde73b46`, có chép dữ liệu cũ từ profile).
- Prompt v2 `chat-turn-v2`: câu trộn Việt–Anh, span chép nguyên văn, giữ ý, không nhận xét phát âm, từ chối prompt injection.
- Thẻ sửa: câu gốc, câu sửa, phần thay đổi; gợi ý tùy chọn tách riêng. Chế độ học mở sẵn; chế độ giao tiếp có nút "Xem lỗi".
- Bộ 30 câu `tests/data/eval_sentences.json` và script `python -m scripts.run_eval` (cần `RUN_LIVE_AI=1`; ghi `ai_runs` với operation `eval`; dừng khi hết hạn mức hoặc gặp 429).
- AC đã đạt (phần đường ống):
  - **AC02**: `test_ac02_error_is_stored_and_shown_as_corrected_sentence`.
  - **AC03**: `test_ac03_correct_sentence_has_no_card`, `test_ac03_style_tip_is_optional_and_separate`.
  - **AC04**: `test_ac04_learning_mode_opens_the_card`, `test_ac04_conversation_mode_closes_the_card_behind_xem_loi`, `test_ac04_each_conversation_keeps_its_own_mode`.
  - Phần "tổng kết vẫn truy cập được" của AC04 làm ở FR10.
- **Chất lượng Gemini thật chưa được chấm:** chủ dự án tự chạy `python -m scripts.run_eval` rồi chấm file kết quả (bước này cần gọi API thật nên chưa chạy).
- Sửa thêm một lỗi cũ: thuộc tính `hidden` bị CSS `.button` ghi đè (nút Dừng luôn hiện).

## Bước tiếp theo
1. FR03: trợ giúp khi bí (3 mức gợi ý và ý bằng tiếng Việt, AC07).
2. Đọc hội thoại, bước 3: Tạm dừng/Tiếp tục, Trước/Sau, tốc độ 0,75/1,0.
3. Đọc hội thoại, bước 4: thông báo khi thiếu giọng hoặc trình duyệt không hỗ trợ; ghi chú FR09 trong SPEC; tài liệu `06`.

## Nợ tài liệu
- `docs/learning/06-read-aloud.md`: làm cùng đọc hội thoại bước 4.

## Chờ quyết định
- **Deploy public cho người khác test.** `CLAUDE.md` cấm khi chưa có đăng nhập, HTTPS và rate limit. Ngoài ra app đang dùng key Gemini của chủ dự án. Cần một kế hoạch riêng trước khi làm.

## Ý tưởng sau (không làm bây giờ)
- `.venv` đang là Python 3.13.13, còn CLAUDE.md/Dockerfile là 3.12: nên thống nhất một phiên bản.
- Khóa phiên bản dependency (`requirements.lock.txt`) theo yêu cầu bàn giao MVP.
- SPEC mục 7–8 còn nhắc SQLite: cập nhật sang Postgres.
- FR01: chatbot mở đầu bằng một câu hỏi ngắn khi tạo hội thoại.
- Lượt `pending` bị kẹt nếu server sập giữa lúc gọi AI: coi `pending` quá 65 giây là `failed` để thử lại được.
- Lưu `suggested_words` (hiện chỉ có trong output AI, chưa lưu, chưa trả qua API).
- Đưa giới hạn 2.000 ký tự (`MAX_MESSAGE_CHARS`) vào `Settings`.
- Harness: giới hạn context theo token; lưu `token_usage` vào `ai_runs`.
- Phân biệt 429 "theo ngày" và "theo phút" hiện dựa vào chữ `PerDay` trong `details` (phỏng đoán, tài liệu Google không nói rõ). Cần xác nhận khi gặp 429 thật.
- Console Windows mặc định cp1252 nên `print` chữ tiếng Việt bị lỗi: đặt `PYTHONIOENCODING=utf-8` khi chạy script thử.
- Hiện giờ gửi theo múi giờ profile (Postgres đổi được múi giờ; hoặc thêm `tzdata`, phải hỏi trước).
- Thêm `favicon.ico` (console báo 404, vô hại).
- Test e2e tự động bằng trình duyệt trong `tests/e2e` (cần thêm Playwright cho Python, phải hỏi trước).
- Thử lại một lượt `failed` ngay trong lịch sử sau khi tải lại trang.
- Điền sẵn trình độ/cách sửa của profile vào hộp thoại tạo hội thoại.
