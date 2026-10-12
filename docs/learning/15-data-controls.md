# 15. Xóa dữ liệu, cờ "Cần xem lại", trang Cài đặt (Mốc 4)

## Mục tiêu
- SPEC mục 9:
  - "Xóa hội thoại xóa messages, corrections và liên kết nguồn; từ đã lưu được giữ nhưng bỏ liên kết."
  - "Có chức năng Xóa toàn bộ dữ liệu học."
- Minh bạch về AI:
  - Dòng nhắc "AI có thể sai" dưới ô nhập.
  - Nút ⚑ "Cần xem lại" trên mỗi câu trả lời của chatbot.
  - Trang Cài đặt cho biết đang dùng AI nào, model nào, hôm nay đã dùng bao nhiêu lượt.
- Đây là phần "xóa dữ liệu" của Mốc 4 (SPEC mục 10). Nó phục vụ nghiệm thu chung AC01–AC08, chứ không gắn với một AC riêng.

## File đã tạo/sửa
| File | Vai trò |
|---|---|
| `alembic/versions/..._6b4805d7e736_add_message_needs_review_flag.py` | Thêm cột `messages.needs_review` (bool, mặc định `false`) |
| `app/models/message.py` | Thuộc tính `needs_review` |
| `app/services/data_service.py` | `delete_conversation`, `delete_all`, `set_needs_review`, `calls_today` |
| `app/schemas/data.py` | `DeleteAllIn {confirm}`, `ReviewFlagIn`, `ReviewFlagOut` |
| `app/routers/data.py` | `DELETE /api/conversations/{id}`, `POST /api/data/delete-all`, `POST /api/messages/{id}/review-flag` |
| `app/dependencies.py`, `app/main.py` | `DataServiceDep`, gắn router |
| `app/routers/pages.py`, `templates/settings.html`, `static/js/settings-page.js` | Trang `/settings` |
| `templates/chat.html`, `_macros.html`, `static/js/chat.js`, `static/css/chat.css` | Nút 🗑 và hộp xác nhận, nút ⚑, dòng nhắc AI |
| `app/schemas/conversation.py` | `MessageOut.needs_review` |
| `tests/integration/test_data_controls.py` | 7 test cho các phần trên |

## Khái niệm mới

### `ON DELETE CASCADE`: để DB tự xóa dữ liệu con
Khi tạo khóa ngoại, có thể khai báo `ON DELETE CASCADE`. Từ đó, lúc xóa dòng cha, Postgres tự xóa luôn các dòng con trỏ tới nó:
```python
conversation_id: Mapped[int] = mapped_column(
    ForeignKey("conversations.id", ondelete="CASCADE")
)
```
Ở dự án này các khóa ngoại đã khai báo CASCADE từ trước, theo chuỗi `conversations → messages → corrections / vocabulary_sources`. Vì vậy `delete_conversation` chỉ cần xóa đúng một dòng `conversations`, còn DB lo phần còn lại, trong cùng một transaction. Bảng `vocabulary` **không** trỏ tới `messages`; chỉ `vocabulary_sources` trỏ tới. Nhờ vậy, khi xóa hội thoại thì từ đã lưu vẫn còn, chỉ mất liên kết nguồn. Đây đúng là điều spec yêu cầu.

### Xóa hàng loạt bằng `delete()`
```python
session.execute(delete(Vocabulary).where(Vocabulary.profile_id == profile.id))
```
Lệnh này sinh ra đúng một câu `DELETE ... WHERE ...`, không cần nạp từng object lên Python. Phù hợp với "Xóa toàn bộ".

### Cụm xác nhận gõ tay
Hành động không hoàn tác được thì yêu cầu người dùng gõ một cụm cố định (`XÓA TẤT CẢ`), thay vì chỉ bấm OK. Server cũng kiểm tra lại cụm này. Như vậy, kể cả gọi thẳng API mà sai cụm cũng bị trả 422 `confirmation_mismatch`. Khi so sánh, server bỏ khoảng trắng hai đầu và không phân biệt hoa thường.

## Luồng chạy
1. **Xóa hội thoại:**
   - Bấm 🗑 thì `<dialog>` xác nhận mở ra. Bấm "Xóa" thì gửi `DELETE /api/conversations/{id}` và nhận 204.
   - JS chuyển về `/`, trang này mở hội thoại gần nhất còn lại.
   - Id không tồn tại thì trả 404 `conversation_not_found`.
2. **Xóa toàn bộ** (trang Cài đặt):
   - Gõ cụm xác nhận, gửi `POST /api/data/delete-all`.
   - Server xóa conversations (kéo theo mọi thứ bên dưới), vocabulary (kéo theo review_events và sources) và lookup_cache.
   - Profile được giữ lại.
3. **Cờ ⚑:**
   - Gửi `POST /api/messages/{id}/review-flag {needs_review}`.
   - Chỉ tin của chatbot mới được gắn cờ; tin của người học trả 404 `reply_not_found`.
   - Nút đổi thành "⚑ Đã đánh dấu" (`aria-pressed="true"`). Tải lại trang vẫn giữ trạng thái.

## Quyết định và lý do
- **Giữ `ai_runs` khi xóa toàn bộ.** Bảng này chỉ chứa metadata (không có câu chat) và dùng để đếm `DAILY_AI_LIMIT`. Nếu xóa luôn bảng này thì "xóa dữ liệu" trở thành cách lách hạn mức ngày.
- **Xóa `lookup_cache` khi xóa toàn bộ.** Cache chứa câu lấy từ hội thoại, tức là dữ liệu học của người dùng.
- **Cờ ⚑ là một cột bool trên `messages`, không phải bảng riêng.** Hiện chỉ cần biết có hay không. Nếu sau này cần ghi chú lý do thì sẽ tạo bảng riêng bằng migration mới.
- **Trang Cài đặt chỉ hiển thị, không cho đổi provider.** Provider và key thuộc `.env`, phía server; trình duyệt không được chạm tới.

## Cách chạy và tự test
```bash
alembic upgrade head
pytest tests/integration/test_data_controls.py -q
```
Thử tay với `AI_PROVIDER=fake`:
1. Tạo một hội thoại mới, gửi một câu, bấm ⚑, rồi tải lại trang. Nút phải vẫn là "Đã đánh dấu".
2. Bấm 🗑, chọn "Xóa". Hội thoại phải biến mất; trang Từ vựng vẫn còn các từ đã lưu.
3. Vào Cài đặt, gõ sai cụm xác nhận. Phải hiện "Hãy gõ đúng “XÓA TẤT CẢ”…" và không có dữ liệu nào bị xóa.

**Đừng thử "Xóa toàn bộ" thật trên DB dev nếu còn muốn giữ dữ liệu.** Phần này đã có test integration chạy trên DB test.

## Lỗi đã gặp
- Khi kiểm tra trên trình duyệt, `page.fill('textarea')` khớp nhầm ô "ý tiếng Việt" của khung trợ giúp (đang ẩn), nên bị timeout. Đã sửa bằng selector cụ thể `#message-input`. Đây là lỗi của kịch bản thử, không phải lỗi của app.
- Console báo `422` khi gõ sai cụm xác nhận. Đây là phản hồi mong đợi; trình duyệt luôn ghi lại mọi response 4xx.
