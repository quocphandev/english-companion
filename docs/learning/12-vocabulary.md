# 12. Lưu và quản lý từ vựng (FR06)

## Mục tiêu
- Trong thẻ nghĩa, bấm **Lưu từ**. Người học có thể sửa nghĩa trước khi lưu.
- **Không lưu trùng**: cùng dạng gốc và cùng nghĩa (sau khi chuẩn hóa) thì không tạo mục mới, chỉ thêm câu nguồn. Cùng từ nhưng **khác nghĩa** thì tạo mục riêng.
- Lưu lỗi thì thẻ giữ nguyên dữ liệu để thử lại; lưu thành công thì báo "Đã lưu".
- Trang **Từ vựng** có tìm kiếm, sửa ghi chú, và xóa có hộp xác nhận.
- Xóa hội thoại (hoặc tin nhắn) thì **từ vẫn được giữ**, chỉ mất liên kết tới câu nguồn.
- FR06. **AC06 đạt**: lưu cùng từ cùng nghĩa không tạo bản trùng; khác nghĩa thì thành mục riêng; dữ liệu nằm trong Postgres nên còn nguyên sau khi khởi động lại.
- Bộ lọc "chưa ôn / đã ôn" làm cùng FR07 (ôn tập).

## Các file
| File | Vai trò |
|---|---|
| `app/models/vocabulary.py` + migration `645587332c7e` | `Vocabulary` (unique `profile_id, lemma, meaning_key`), `VocabularySource` |
| `app/services/vocabulary_service.py` | `normalize_lemma`, `meaning_key`, lưu/tìm/sửa/xóa |
| `app/repositories/vocabulary_repository.py` | Truy vấn; tìm kiếm bằng `ILIKE` có tham số |
| `app/schemas/vocabulary.py` | `SaveWordIn`, `UpdateWordIn`, `WordOut`, `SaveWordResponse` |
| `app/routers/vocabulary.py` | `GET/POST /api/vocabulary`, `PATCH/DELETE /api/vocabulary/{id}` |
| `app/templates/_app_layout.html` | Khung trang dùng chung (thanh bên, hộp thoại), tách ra từ `chat.html` |
| `app/templates/vocabulary.html`, `static/js/vocab/vocabulary-page.js` | Trang Từ vựng |
| `static/js/vocab/lookup.js` | Khung "Lưu từ" trong thẻ nghĩa |

## Khái niệm

### Chuẩn hóa để phát hiện trùng
```python
meaning_key("  Đặt (phòng)! ") == meaning_key("đặt phòng")  # True
meaning_key("đặt") == meaning_key("dat")  # False: giữ dấu tiếng Việt
```
- Bỏ khác biệt về chữ hoa/thường, khoảng trắng và dấu câu.
- **Giữ dấu tiếng Việt**, vì bỏ dấu sẽ gộp nhầm các nghĩa khác nhau.
- `unicodedata.normalize("NFC")` gộp hai cách gõ dấu (dấu dựng sẵn và dấu tổ hợp) về một dạng.

Ràng buộc unique `(profile_id, lemma, meaning_key)` nằm **trong DB**. Nếu hai request lưu cùng lúc, DB sẽ chặn bản thứ hai và service đọc lại bản đã có, giống cách xử lý `request_id` ở bài 04.

### Không tin dữ liệu từ trình duyệt
Trình duyệt chỉ gửi `message_id`, vị trí và nghĩa (đã sửa). Server tự làm phần còn lại:
1. Đọc lại câu từ tin nhắn trong DB.
2. Tính khóa cache và lấy kết quả tra đã có (dạng gốc, từ loại, ví dụ).
3. Nếu chưa từng tra thì từ chối (`409 lookup_required`).

Spec gọi đây là "lưu lookup đã xác thực".

### `<dialog>` với `method="dialog"`
```html
<form method="dialog">
  <button value="cancel">Hủy</button><button value="confirm">Xóa</button>
</form>
```
Bấm nút nào thì hộp thoại đóng, và `dialog.returnValue` mang giá trị của nút đó. Cách này không cần `window.confirm`, nên giao diện tiếng Việt, đồng bộ với phần còn lại, và dùng được bằng bàn phím.

### Kế thừa template nhiều tầng
```
base.html  →  _app_layout.html (thanh bên + hộp thoại)  →  chat.html / vocabulary.html
```
Thanh bên chỉ viết một lần, mỗi trang chỉ điền phần `{% block main %}` của mình.

### Xóa hội thoại nhưng giữ từ
`vocabulary_sources.message_id` có `ON DELETE CASCADE`: xóa tin nhắn thì dòng liên kết bị xóa. Bảng `vocabulary` không tham chiếu tới tin nhắn, nên từ vẫn còn. Điều này đúng với yêu cầu phi chức năng của spec: "từ đã lưu được giữ nhưng bỏ liên kết".

## API
| Gọi | Kết quả |
|---|---|
| `POST /api/vocabulary {message_id, start, end, meaning_vi}` | 201 `created: true`, hoặc 200 `created: false` nếu đã có |
| `GET /api/vocabulary?q=sách` | Danh sách, mới nhất trước |
| `PATCH /api/vocabulary/{id} {note}` hoặc `{meaning_vi}` | Từ đã sửa; nếu nghĩa mới trùng một mục khác thì 409 `duplicate_meaning` |
| `DELETE /api/vocabulary/{id}` | 204; không tìm thấy thì 404 `word_not_found` |

## Cách tự test
```powershell
pytest tests/unit/test_vocabulary_keys.py tests/integration/test_vocabulary_api.py -v
```
Trên giao diện:
1. Bấm một từ, sửa nghĩa, bấm "Lưu từ": thấy "Đã lưu vào sổ từ".
2. Bấm "Lưu từ" lần nữa: thấy "Từ này với nghĩa đó đã có trong sổ từ".
3. Mở "Từ vựng" ở thanh bên: tìm từ, sửa ghi chú, xóa (có hộp xác nhận).
