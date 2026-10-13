# Progress

## Đang ở mốc
MVP (Mốc 1–4) đã xong. Mốc 5 (giọng nói: micro, STT) chưa bắt đầu: cần chọn nhà cung cấp STT và chấp nhận chi phí trước.

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

## FR03, trợ giúp khi bí — xong (merge từ `feat/FR03-help`)
- `POST /api/help`: mức 1 gợi ý từ, 2 mở đầu câu, 3 câu mẫu, hoặc ý tiếng Việt (`intent_vi`). Bảng `help_requests` lưu lịch sử dùng trợ giúp (migration `9aa185351c36`).
- Giao diện: nút "Giúp tôi" mở khung trợ giúp trên ô nhập; "Chèn vào ô nhập" chỉ chèn, không gửi.
- Phần chung: `run_structured` (harness cho mọi schema), `AiUsage` (hạn mức + `ai_runs`), FakeProvider theo schema.
- **AC07 đạt**: `test_ac07_help_never_creates_a_message` và kiểm tra trên trình duyệt (chỉ gọi `/api/help`, không gọi API gửi tin).

## FR01, câu hỏi mở đầu — xong (merge từ `feat/FR01-opener`)
- Hội thoại mới có sẵn một câu hỏi của chatbot, tạo theo mẫu (không gọi AI): không tốn lượt, không phải chờ, không lỗi.
- Câu mở đầu được giữ trong ngữ cảnh gửi cho AI, đặt sau một lượt user trung tính `(Start of the conversation.)`.
- Test: `test_new_conversation_starts_with_the_chatbot_question`, `test_opening_question_is_shown_first_and_escaped`, `tests/unit/test_opener.py`.

## Đọc hội thoại (FR09, bản trình duyệt) — xong (merge từ `feat/FR09-reader-controls`)
- Tạm dừng/Tiếp tục (tự làm bằng `cancel()`), Trước/Sau, tốc độ 0,75/1,0 (có hiệu lực từ câu sau).
- Báo thiếu giọng một lần cho mỗi ngôn ngữ; trình duyệt không hỗ trợ thì hiện "Trình duyệt chưa hỗ trợ đọc".
- Lỗi nghiêm trọng của trình duyệt (`not-allowed`, `synthesis-unavailable`...) thì dừng đọc, chat vẫn dùng bình thường.
- Sửa thêm: file tĩnh có `Cache-Control: no-cache`, nên trình duyệt không chạy JS cũ sau khi cập nhật.
- Ghi chú FR09 trong `docs/SPEC.md`; tài liệu `06`.
- Test: `tests/js/reading-queue.test.mjs` (nextMessage, previousMessage), `test_reader_bar_is_rendered_hidden_with_its_controls`, `test_static_files_are_revalidated_by_the_browser`. Các trạng thái đã kiểm tra trên trình duyệt (Playwright).

## Mốc 3 — FR05, tra nghĩa theo ngữ cảnh — xong (merge từ `feat/FR05-lookup`)
- `POST /api/lookup` (message_id + vị trí theo code point). Server tự lấy câu, đánh dấu `⟦…⟧`, cache theo câu + vùng chọn + ngôn ngữ + phiên bản prompt (bảng `lookup_cache`, migration `2ea2d64cf519`).
- Giao diện: từ trong tin của chatbot bấm được; "Tra cụm" khi bôi đen chữ; chế độ "Chọn cụm" (chạm từ đầu rồi từ cuối, tối đa 8 từ); thẻ nghĩa hiện ngay dưới tin nhắn.
- **AC05 đạt phần đường ống**: `test_ac05_book_as_noun_and_verb_are_separate_lookups`, `test_ac05_phrase_looks_after_is_looked_up_as_a_whole`; cache: `test_second_identical_lookup_comes_from_cache_without_ai`. Nghĩa thật do Gemini trả cần người kiểm tra.

## Mốc 3 — FR06, lưu và quản lý từ — xong (merge từ `feat/FR06-vocabulary`)
- Bảng `vocabulary` (unique `profile_id, lemma, meaning_key`) và `vocabulary_sources` (migration `645587332c7e`). Xóa tin nhắn thì mất liên kết, từ vẫn giữ.
- `POST/GET/PATCH/DELETE /api/vocabulary`. Lưu dựa trên kết quả tra đã có trong cache (server tự đọc lại câu); người học sửa được nghĩa trước khi lưu.
- Thẻ nghĩa có "Lưu từ"; trang "Từ vựng" có tìm kiếm, ghi chú, xóa có xác nhận. Thanh bên dùng chung qua `_app_layout.html`.
- **AC06 đạt**: `test_ac06_same_word_same_meaning_is_not_duplicated`, `test_ac06_same_word_with_another_meaning_is_a_separate_entry`; giữ từ khi xóa tin nhắn: `test_deleting_the_message_keeps_the_word_but_drops_the_link`.

## Mốc 4 — FR07, ôn tập thủ công (MVP) — xong (merge từ `feat/FR07-review`)
- Bảng `review_events` (migration `9c34ce25e825`); `POST /api/reviews`, `GET /api/reviews/deck`.
- Trang "Ôn tập": mặt trước là từ kèm câu khuyết (từ câu nguồn, hoặc từ câu ví dụ), mặt sau là nghĩa và ví dụ; Nhớ / Chưa nhớ; tổng kết cuối lượt.
- Thứ tự: chưa ôn, rồi chưa nhớ, rồi đã nhớ. Trang Từ vựng lọc được chưa ôn / đã ôn.
- Test: `tests/integration/test_review_api.py` (ghi kết quả, thứ tự thẻ, câu khuyết, bộ lọc, trang), `tests/unit/test_review_cloze.py`.
- Lịch ôn cách quãng và đưa từ vào hội thoại thuộc giai đoạn 3 (chưa làm).

## Mốc 4 — FR10, kết thúc buổi và tổng kết — xong (merge từ `feat/FR10-summary`)
- `POST /api/conversations/{id}/finish` (migration `297a91fab8db`): lỗi và từ lấy từ DB, AI viết tóm tắt và bài luyện tiếp theo; AI chỉ được thêm từ có xuất hiện trong hội thoại.
- AI lỗi hoặc hết hạn mức vẫn kết thúc buổi; kết thúc lần hai không gọi AI; buổi đã xong thì chặn tin mới và trợ giúp (409).
- Trang: nút "Kết thúc buổi" có hộp xác nhận; buổi đã xong thì hiện bản tổng kết thay ô nhập; thanh bên gắn nhãn "đã xong".
- **AC04 đạt đủ** (phần tổng kết): `test_ac04_conversation_mode_errors_are_in_the_summary`. Test khác trong `tests/integration/test_summary_api.py`, `tests/unit/test_summary.py`.

## Mốc 4 — Xóa dữ liệu và minh bạch AI — xong (merge từ `feat/M4-data-controls`)
- Xóa một hội thoại (nút 🗑 + hộp xác nhận): messages, corrections, help_requests và liên kết nguồn bị xóa theo CASCADE; từ đã lưu vẫn giữ.
- Xóa toàn bộ dữ liệu học ở trang Cài đặt: phải gõ `XÓA TẤT CẢ`. Xóa hội thoại, từ vựng, kết quả ôn và cache tra nghĩa; giữ `ai_runs` để không lách được hạn mức ngày.
- Nút ⚑ "Cần xem lại" trên câu trả lời của chatbot (cột `messages.needs_review`, migration `6b4805d7e736`); dòng nhắc "AI có thể sai" dưới ô nhập; trang Cài đặt hiện provider, model và số lượt hôm nay.
- Test: `tests/integration/test_data_controls.py` (7 test). Đã thử trên trình duyệt: gắn/bỏ cờ còn sau khi tải lại, xóa hội thoại, sai cụm xác nhận bị chặn. Tài liệu `15`.

## Bàn giao MVP — xong (merge từ `chore/M4-handover`)
- `README.md`: cài đặt cho Windows và macOS, chọn AI, lệnh hằng ngày, lỗi hay gặp.
- `requirements.lock.txt`: phiên bản đã thử (pip freeze, Python 3.13). Dockerfile vẫn dùng `requirements.txt`.
- `python -m scripts.seed_demo`: thêm một hội thoại demo và 2 từ (`book`, `look after`); không gọi AI, không xóa gì, chạy lại thì bỏ qua. Test: `tests/integration/test_seed_demo.py`.

## Bảng nghiệm thu AC01–AC08 (Mốc 4)
"Đường ống" nghĩa là đã kiểm bằng test tự động với provider giả. "Chất lượng" là nội dung Gemini trả về thật, cần người chấm bằng `scripts.run_eval`.

| AC | Trạng thái | Bằng chứng |
|---|---|---|
| AC01 | Đạt | `tests/integration/test_conversations_api.py` (câu rỗng/quá dài, trùng `request_id`, gửi đồng thời) |
| AC02 | Đạt đường ống; chất lượng chờ chấm | `test_ac02_error_is_stored_and_shown_as_corrected_sentence`; eval câu sai |
| AC03 | Đạt đường ống; chất lượng chờ chấm | `test_ac03_correct_sentence_has_no_card`, `test_ac03_style_tip_is_optional_and_separate`; eval câu đúng |
| AC04 | Đạt | `test_ac04_learning_mode_opens_the_card`, `test_ac04_conversation_mode_closes_the_card_behind_xem_loi`, `test_ac04_conversation_mode_errors_are_in_the_summary` |
| AC05 | Đạt đường ống; nghĩa thật chờ người kiểm | `test_ac05_book_as_noun_and_verb_are_separate_lookups`, `test_ac05_phrase_looks_after_is_looked_up_as_a_whole` |
| AC06 | Đạt | `test_ac06_same_word_same_meaning_is_not_duplicated`, `test_ac06_same_word_with_another_meaning_is_a_separate_entry`; dữ liệu ở Postgres, còn sau restart (đã thử tay) |
| AC07 | Đạt | `test_ac07_help_never_creates_a_message`; "Chèn vào ô nhập" chỉ chèn, sửa được trước khi gửi (đã thử trên trình duyệt) |
| AC08 | Đạt | `test_invalid_json_is_repaired_with_one_extra_call`, `test_still_invalid_after_repair_fails_without_third_call`, `test_provider_error_returns_structured_error_and_keeps_text`; key sai → `ai_auth_failed` (smoke test live) |

AC09, AC10 thuộc Mốc 5 (giọng nói), chưa làm.

## Bản demo public (Render + Neon) — code xong (merge từ `feat/deploy-render`)
- Mật khẩu chung `APP_PASSWORD` (HTTP Basic, trừ `/health`); rate limit `RATE_LIMIT_PER_MINUTE` theo IP cho các endpoint gọi AI (429 `rate_limited`); `PUBLIC_DEMO=true` tắt xóa (403 `deleting_disabled`) và bắt buộc có mật khẩu.
- Dockerfile: Python 3.13 + `requirements.lock.txt`, migration khi khởi động, cổng `$PORT`; sửa lỗi `adduser`. `render.yaml` (Blueprint). README có hướng dẫn deploy.
- Test: `tests/unit/test_security.py`, `test_public_demo_disables_deleting`. Đã chạy container thật với AI giả trên DB trống `english_companion_deploycheck`: migration, 401/200, 429 ở tin thứ 4, xóa bị 403.
- **Chưa deploy thật**: cần chủ dự án tạo tài khoản Neon, Render, key Gemini riêng (xem README).
- **Chưa cập nhật quy tắc trong `CLAUDE.md`** (Claude bị chặn tự sửa file quy tắc): chủ dự án tự sửa mục Bảo mật và "Ngoài phạm vi".

## Bước tiếp theo
- Chủ dự án chạy `$env:RUN_LIVE_AI="1"; python -m scripts.run_eval` rồi chấm file trong `eval_results/` để chốt chất lượng AC02, AC03, AC05.
- Deploy bản demo theo README (Neon + Render), rồi mở link thử.
- Quyết định có bắt đầu Mốc 5 hay không (chọn nhà cung cấp STT, chi phí).

## Chờ quyết định
- Xóa DB thử `english_companion_deploycheck` trên Postgres local (chỉ chứa dữ liệu thử).

## Ý tưởng sau (không làm bây giờ)
- `.venv` đang là Python 3.13.13, còn CLAUDE.md/Dockerfile là 3.12: nên thống nhất một phiên bản, rồi cho Dockerfile cài từ `requirements.lock.txt`.
- SPEC mục 7–8 còn nhắc SQLite: cập nhật sang Postgres.
- FR01: có thể chuyển câu mở đầu sang do AI sinh (hiện dùng mẫu).
- Lượt `pending` bị kẹt nếu server sập giữa lúc gọi AI: coi `pending` quá 65 giây là `failed` để thử lại được.
- Lưu `suggested_words` (hiện chỉ có trong output AI, chưa lưu, chưa trả qua API).
- Đưa giới hạn 2.000 ký tự (`MAX_MESSAGE_CHARS`) vào `Settings`.
- Harness: giới hạn context theo token; lưu `token_usage` vào `ai_runs`.
- Phân biệt 429 "theo ngày" và "theo phút" hiện dựa vào chữ `PerDay` trong `details` (phỏng đoán, tài liệu Google không nói rõ). Cần xác nhận khi gặp 429 thật.
- Console Windows mặc định cp1252 nên `print` chữ tiếng Việt bị lỗi: đặt `PYTHONIOENCODING=utf-8` khi chạy script thử.
- Hiện giờ gửi theo múi giờ profile (Postgres đổi được múi giờ; hoặc thêm `tzdata`, phải hỏi trước).
- Thêm `favicon.ico` (console báo 404, vô hại).
- Bản demo: đăng nhập theo từng người để mỗi người có dữ liệu riêng (hiện dùng chung một profile).
- Rate limit: chỉ tin IP cuối do proxy Render thêm vào thay vì `--forwarded-allow-ips='*'`.
- Test e2e tự động bằng trình duyệt trong `tests/e2e` (cần thêm Playwright cho Python, phải hỏi trước).
- Thử lại một lượt `failed` ngay trong lịch sử sau khi tải lại trang.
- Điền sẵn trình độ/cách sửa của profile vào hộp thoại tạo hội thoại.
