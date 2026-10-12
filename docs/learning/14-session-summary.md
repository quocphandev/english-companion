# 14. Kết thúc buổi và tổng kết (FR10)

## Mục tiêu
- Nút **Kết thúc buổi** (có hộp xác nhận) tạo bản tổng kết gồm:
  - Tóm tắt nội dung đã nói.
  - Tối đa 5 lỗi cần ôn.
  - Tối đa 5 từ quan trọng.
  - Một gợi ý bài luyện tiếp theo.
  - Số lần đã dùng "Giúp tôi".
- **Không bịa thông tin**: lỗi và từ lấy từ dữ liệu thật của buổi học. AI chỉ được thêm từ khi từ đó thực sự xuất hiện trong hội thoại.
- **AI lỗi hoặc hết hạn mức thì vẫn kết thúc buổi**, vẫn có danh sách lỗi và từ; chỉ thiếu phần tóm tắt.
- Buổi đã kết thúc thì không gửi thêm tin, nhưng vẫn xem lịch sử, vẫn tra từ và vẫn đọc hội thoại được.
- FR10. **AC04 đạt đủ**: ở chế độ giao tiếp, lỗi vẫn xem được qua "Xem lỗi" **và qua bản tổng kết**.

## Các file
| File | Vai trò |
|---|---|
| Migration `297a91fab8db` | Thêm `conversations.finished_at` và `summary_details` (JSONB) |
| `app/schemas/ai.py` (`SummaryReply`), `app/schemas/summary.py` (`SessionSummary`) | Schema đầu ra của AI và của API |
| `app/harness/summary_context.py`, `prompts.py` (`SUMMARY_PROMPT_VERSION`) | Gửi toàn bộ buổi học trong một lượt user |
| `app/services/summary_service.py` | `pick_errors`, `pick_words`, `finish`, `summary_of` |
| `app/routers/conversations.py` | `POST /api/conversations/{id}/finish` |
| `conversation_service.py`, `help_service.py` | Buổi đã xong thì trả 409 `conversation_finished` |
| `templates/_macros.html` (`render_summary`), `chat.html`, `static/js/chat.js` (`setupFinish`) | Giao diện |

## Khái niệm

### Chia việc giữa dữ liệu thật và AI
| Phần | Nguồn | Lý do |
|---|---|---|
| Lỗi cần ôn | Bảng `corrections` (bỏ `naturalness`, mỗi cách sửa chỉ lấy một lần) | Đúng những gì đã xảy ra |
| Từ quan trọng | Từ đã lưu trong buổi, rồi tới từ AI gợi ý **có xuất hiện** trong hội thoại | Chặn AI bịa từ |
| Tóm tắt, bài luyện tiếp | AI | Cần diễn đạt tự nhiên |

### Kết thúc không phụ thuộc AI
```python
reply, ai_error = self._ask_ai(conversation)  # có thể lỗi, có thể hết hạn mức
conversation.status = "finished"  # vẫn luôn kết thúc
```
Hết hạn mức ngày thì **không chặn** việc kết thúc buổi, chỉ ghi lại lỗi để giao diện báo "chưa tạo được phần tóm tắt".

### Gọi hai lần cũng không sao
Kết thúc một buổi đã kết thúc thì trả lại bản tổng kết đã lưu, **không gọi AI lần nữa**. Đây là cùng ý tưởng idempotency đã dùng ở bài 04.

### Lưu dữ liệu bán cấu trúc bằng JSONB
`summary_details` lưu bài luyện tiếp theo, từ do AI gợi ý và lỗi AI (nếu có). Các giá trị này chỉ dùng để hiển thị, không dùng để lọc hay tìm kiếm, nên một cột JSONB gọn hơn tạo nhiều cột riêng.

## API
```http
POST /api/conversations/12/finish
→ 200 {"conversation_id": 12, "finished_at": "...", "recap_vi": "...", "next_exercise_vi": "...",
       "errors": [...], "words": [{"text": "...", "meaning_vi": "...", "saved": true}],
       "help_count": 1, "ai_error": null}
```
Sau khi kết thúc: gửi tin mới hoặc gọi trợ giúp trả 409 `conversation_finished`; gửi lại một lượt đã xong (cùng `request_id`) vẫn trả kết quả cũ.

## Cách tự test
```powershell
pytest tests/unit/test_summary.py tests/integration/test_summary_api.py -v
```
Trên giao diện: chat vài câu, bấm "Kết thúc buổi", rồi "Kết thúc". Trang hiện bản tổng kết thay cho ô nhập, thanh bên gắn nhãn "đã xong".
