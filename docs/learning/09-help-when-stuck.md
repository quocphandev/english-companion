# 09. Trợ giúp khi bí ("Giúp tôi") và harness tổng quát

## Mục tiêu
- Khi bí, người học bấm **Giúp tôi** và chọn một trong 4 cách:
  1. Gợi ý từ: tối đa 3 từ, kèm nghĩa Việt.
  2. Mở đầu câu: khung câu để tự viết tiếp.
  3. Câu mẫu: một câu hoàn chỉnh.
  4. Nhập ý bằng tiếng Việt: nhận cách nói bằng tiếng Anh và lời giải thích.
- Gợi ý **không bao giờ tự gửi**. Nút "Chèn vào ô nhập" chỉ đưa chữ vào ô nhập; người học sửa rồi tự bấm Gửi.
- Mỗi lần dùng trợ giúp được lưu lại để xem về sau, không dùng làm điểm phạt.
- FR03. **AC07 đạt.**

## Các file
| File | Vai trò |
|---|---|
| `app/harness/chat_harness.py` | `run_structured(request, schema)`: harness dùng chung cho mọi tác vụ AI; `run_turn` và `run_help` đều dùng nó |
| `app/harness/help_context.py` | `HelpContext`, `help_mode_for`, `build_help_request` |
| `app/harness/prompts.py` | `HELP_PROMPT_VERSION`, `HELP_MODE_INSTRUCTIONS`, `HELP_SYSTEM_PROMPT_TEMPLATE` |
| `app/schemas/ai.py` | `HelpReply` (`hint_en`, `words` tối đa 3, `explanation_vi`) |
| `app/schemas/help.py` | `HelpRequestIn`, `HelpResponse` |
| `app/services/ai_usage.py` | `AiUsage`: kiểm tra hạn mức ngày và ghi `ai_runs`, dùng chung cho chat, trợ giúp và các tác vụ sau |
| `app/services/help_service.py` | Nghiệp vụ trợ giúp |
| `app/routers/help.py` | `POST /api/help` |
| `app/models/help_request.py` + migration `9aa185351c36` | Bảng `help_requests`; mở rộng `ai_runs.operation` |
| `app/providers/fake_provider.py` | Trả câu mẫu phù hợp với **schema** được yêu cầu |
| `templates/chat.html`, `static/js/chat.js`, `static/css/chat.css` | Khung trợ giúp nằm ngay trên ô nhập |
| `tests/unit/test_help_context.py`, `tests/integration/test_help_api.py` | Test |

## Khái niệm

### Harness tổng quát: một vòng lặp cho mọi schema
Chat, trợ giúp, tra từ và tổng kết đều theo cùng một quy trình: gọi AI, kiểm tra JSON theo schema, sai thì sửa 1 lần. Thay vì chép lại vòng lặp cho từng tác vụ:
```python
def run_structured(
    self, request: ProviderRequest, schema: type[BaseModel]
) -> TaskResult:
    ...
    value = schema.model_validate_json(raw_text)  # TurnReply, HelpReply, ...
```
Muốn thêm một tác vụ AI mới, chỉ cần viết schema, prompt và hàm ghép request.

### Lời người học vẫn nằm trong lượt "user"
Ý tiếng Việt do người học nhập được đặt trong **lượt user**, bọc trong `<intent>...</intent>`. Chế độ trợ giúp (từ, khung câu, câu mẫu, ý tiếng Việt) do **app** chọn và đặt trong system. Test `test_vietnamese_idea_goes_in_the_user_turn_never_the_system` kiểm tra điều này.

### Fake provider trả lời theo schema
```python
title = (request.response_schema or {}).get("title", "TurnReply")
return ProviderResponse(text=self._replies[title].model_dump_json())
```
Pydantic đặt `title` của JSON schema bằng tên class (`"HelpReply"`), nên fake provider biết phải trả mẫu nào.

## API
```http
POST /api/help
{"conversation_id": 1, "level": 2}                           → mode "starter"
{"conversation_id": 1, "level": 3, "intent_vi": "Tôi bị kẹt xe"} → mode "intent"
→ 200 {"status": "succeeded", "mode": "...", "hint_en": "...", "words": [...], "explanation_vi": "...", "error": null}
```
| Tình huống | Kết quả |
|---|---|
| `level` ngoài 1–3, ý quá 500 ký tự | 422 `invalid_input` |
| Không có hội thoại | 404 |
| Hết hạn mức ngày | 429 `daily_limit_reached`, không gọi AI |
| AI lỗi | 200, `status: failed`, `error` có cấu trúc |

## Quyết định và lý do
| Quyết định | Lý do |
|---|---|
| Có nhập ý tiếng Việt thì luôn dùng chế độ `intent` | Người học đã nói rõ muốn diễn đạt ý gì |
| "Chèn" sẽ **nối** gợi ý vào chữ đang gõ, không xóa | Không làm mất câu người học đang viết |
| Khung trợ giúp nằm ngay trên ô nhập, không dùng hộp thoại che màn hình | Ô nhập luôn nhìn thấy được, kể cả trên điện thoại |
| Trợ giúp được tính vào `DAILY_AI_LIMIT` | Trợ giúp cũng tốn lượt gọi thật |

## Cách chạy và tự test
```powershell
pytest tests/unit/test_help_context.py tests/integration/test_help_api.py -v
```
Trên giao diện: bấm "Giúp tôi", chọn "2 · Mở đầu câu", rồi bấm "Chèn vào ô nhập". Chữ được thêm vào ô nhập, và **không có tin nào được gửi** cho tới khi bạn bấm Gửi.
