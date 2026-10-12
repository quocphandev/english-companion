# 10. Chatbot mở đầu bằng một câu hỏi (FR01)

## Mục tiêu
FR01: "Chatbot mở đầu bằng một câu hỏi ngắn." Mỗi hội thoại mới có sẵn một tin của chatbot, ví dụ:
> Hi! Let's talk about “coffee shop”. What do you want to tell me first?

## Các file
| File | Vai trò |
|---|---|
| `app/services/opener.py` | `build_opener(topic, level)`: câu hỏi theo mẫu; A1/A2 dùng câu đơn giản hơn |
| `app/services/conversation_service.py` | Khi tạo hội thoại, lưu câu mở đầu **trong cùng transaction** |
| `app/repositories/conversation_repository.py` | `add_assistant_message`: tin của chatbot không trả lời lượt nào |
| `app/harness/context.py` | `CONVERSATION_START`: giữ câu mở đầu trong ngữ cảnh gửi cho AI |
| `app/schemas/conversation.py`, `templates/chat.html` | `ConversationHistory.opener`, hiển thị ở đầu khung chat |
| `tests/unit/test_opener.py`, test integration và test trang | Test |

## Khái niệm: vì sao phải chèn một "lượt mở đầu" giả
API của AI cần lượt **đầu tiên là của user**. Trước đây, nếu lịch sử bắt đầu bằng tin của chatbot, code **bỏ tin đó đi**, và như vậy AI không biết chính nó đã hỏi gì. Giờ code chèn thêm một lượt user trung tính ở trước:
```
user:      (Start of the conversation.)
assistant: Hi! Let's talk about “work”. What do you want to tell me first?
user:      I'm a tester.
```
AI vẫn thấy câu hỏi của mình, mà vẫn đúng quy tắc lượt user đứng đầu.

## Quyết định và lý do
| Quyết định | Lý do |
|---|---|
| Câu mở đầu theo **mẫu**, không gọi AI | Không tốn lượt trong hạn mức, tạo hội thoại xong ngay, không thể lỗi. Có thể chuyển sang AI sinh câu sau này nếu cần |
| Câu mở đầu là tin `assistant` có `reply_to_message_id = NULL` | Phân biệt được với câu trả lời của AI; tính năng đọc hội thoại tự đọc luôn câu này |
| Hội thoại tạo trước tính năng này không có câu mở đầu | Không sửa dữ liệu cũ; giao diện vẫn hiện lời nhắc "Hãy gửi câu tiếng Anh đầu tiên" cho những hội thoại đó |

## Cách tự test
Tạo một hội thoại mới: câu hỏi của chatbot hiện ngay. Chạy test:
```powershell
pytest tests/unit/test_opener.py -v
```
