# 11. Bấm từ, chọn cụm, tra nghĩa theo ngữ cảnh (FR05)

## Mục tiêu
- Mọi từ trong tin của chatbot (kể cả câu mở đầu) đều **bấm được**. Bấm vào thì hiện nghĩa **trong câu đó**: từ loại, dạng gốc, ví dụ, và nghĩa cả câu (mở khi cần).
- Chọn **cụm tối đa 8 từ**:
  - Trên máy tính: bôi đen chữ rồi bấm "Tra cụm".
  - Trên điện thoại (và cả máy tính): bật **Chọn cụm**, chạm từ đầu rồi chạm từ cuối của cụm.
- Dấu câu không phải là từ; các từ có dấu nháy như `don't`, `I’m` vẫn giữ nguyên.
- Khi ngữ cảnh có nhiều cách hiểu: hiện các cách hiểu khác và nói rõ chỗ chưa chắc chắn.
- **Cache** theo bộ (câu, vùng chọn, ngôn ngữ, phiên bản prompt), không bao giờ chỉ theo mặt chữ.
- FR05. **AC05 đạt phần đường ống**: "book" danh từ và "book" động từ là hai lần tra riêng, mỗi lần gửi câu riêng của nó; "looks after" được tra như một cụm. Nghĩa thật do Gemini trả, cần người kiểm tra.

## Các file
| File | Vai trò |
|---|---|
| `app/services/text_selection.py` | Hàm thuần: tách từ, các từ trong vùng chọn, ranh giới câu (tính theo code point) |
| `app/harness/lookup_context.py` | `LookupContext` (câu và vùng chọn), `marked_sentence()` đánh dấu `⟦…⟧`, `lookup_cache_key` |
| `app/harness/prompts.py` | `LOOKUP_PROMPT_VERSION`, `LOOKUP_SYSTEM_PROMPT` |
| `app/schemas/ai.py`, `app/schemas/lookup.py` | `LookupReply`; `LookupRequestIn` và `LookupResponse` |
| `app/models/lookup_cache.py` + migration `2ea2d64cf519` | Bảng `lookup_cache` (kết quả lưu dạng JSONB, `cache_key` unique) |
| `app/repositories/lookup_repository.py` | Đọc và ghi cache (`ON CONFLICT DO NOTHING`) |
| `app/services/lookup_service.py` | Kiểm tra vùng chọn, cache, hạn mức, gọi AI |
| `app/routers/lookup.py` | `POST /api/lookup` |
| `app/static/js/vocab/tokens.js` | Hàm thuần JS: tách từ, đổi vị trí UTF-16 sang code point |
| `app/static/js/vocab/lookup.js` | Biến các từ thành phần tử bấm được, chế độ chọn cụm, nút "Tra cụm", thẻ nghĩa |

## Khái niệm

### Code point và UTF-16
Python đếm chuỗi theo **code point** (mỗi ký tự Unicode tính là 1). JavaScript đếm theo **UTF-16**: hầu hết ký tự tính là 1, nhưng emoji như 😀 tính là 2. Nếu không thống nhất, vị trí gửi lên server sẽ lệch:
```js
"😀 book".indexOf("book")         // 3  (UTF-16)
toCodePoints("😀 book", 3)         // 2  (code point, giống Python)
```
SPEC mục 8 quy định API dùng code point, nên phía trình duyệt phải đổi trước khi gửi.

### Gửi cả câu, đánh dấu vị trí, không gửi từ đứng riêng
```
Sentence: <sentence>I want to ⟦book⟧ a room.</sentence>
```
Nhờ dấu `⟦ ⟧`, AI biết đang hỏi "book" **ở vị trí nào trong câu nào**, nên phân biệt được danh từ hay động từ. Server **tự lấy câu** từ tin nhắn trong DB; trình duyệt chỉ gửi `message_id` và vị trí. Như vậy người dùng không thể gửi một câu tự bịa lên.

### Cache theo ngữ cảnh
```python
key = sha256([prompt_version, "vi", sentence, start, end])
```
Cùng câu và cùng vùng chọn thì lấy từ cache: không gọi AI, không tính lượt. Khác câu, hoặc cùng câu nhưng khác vị trí (ví dụ "**Book** the book"), thì là một khóa khác.

`ON CONFLICT DO NOTHING`: nếu hai lần tra giống nhau ghi cùng lúc, Postgres giữ bản ghi đầu tiên và không báo lỗi.

### Biến từ thành phần tử bấm được mà vẫn an toàn
JS lấy `textContent` của tin nhắn, tách thành từ, rồi tạo `<span class="word">` bằng `createElement`. Không dùng `innerHTML`, nên không có nguy cơ XSS. Tính năng đọc hội thoại vẫn đọc `textContent` như cũ, không bị ảnh hưởng.

## API
```http
POST /api/lookup  {"message_id": 12, "start": 10, "end": 14}
→ 200 {"status": "succeeded", "selected_text": "book", "source_sentence": "I want to book a room.",
       "sentence_start": 10, "sentence_end": 14, "cached": false,
       "lemma": "book", "pos": "verb", "meaning_vi": "đặt", "example_en": "...",
       "sentence_meaning_vi": "...", "alternatives": [], "uncertainty_vi": null, "error": null}
```
| Tình huống | Kết quả |
|---|---|
| Vùng chọn rỗng, chỉ có dấu câu, vượt quá độ dài tin | 422 `invalid_selection` |
| Hơn 8 từ | 422 `selection_too_long` |
| Không có tin nhắn | 404 `message_not_found` |
| Hết hạn mức (khi không có cache) | 429 |
| AI lỗi | 200, `status: failed`, không ghi cache |

## Quyết định và lý do
| Quyết định | Lý do |
|---|---|
| Thẻ nghĩa hiện **ngay dưới tin nhắn**, không dùng popup nổi | Không bao giờ che ô nhập trên điện thoại (yêu cầu của spec); dễ dùng bằng bàn phím |
| Bấm vào giữa một từ thì tra **cả từ** | Tránh tra nửa từ |
| Chỉ cho bấm từ trong tin của chatbot | Spec: "mỗi từ trong phản hồi tiếng Anh"; câu người học thì đã có thẻ sửa |
| Chọn cụm bằng cách chạm 2 lần | Trên điện thoại khó bôi đen chính xác |

## Cách tự test
```powershell
pytest tests/unit/test_text_selection.py tests/unit/test_lookup_context.py tests/integration/test_lookup_api.py -v
node --test "tests/js/**/*.test.mjs"
```
Với Gemini thật: gửi một câu để chatbot trả lời, bấm một từ trong câu trả lời. Thử bôi đen một cụm, hoặc bật "Chọn cụm". Tra lại đúng từ đó thì kết quả trả về ngay (lấy từ cache).
