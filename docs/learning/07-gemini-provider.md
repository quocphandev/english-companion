# 07. GeminiProvider, lỗi có cấu trúc và hạn mức ngày (`ai_runs`)

## Mục tiêu
- Thay fake bằng AI thật: **Gemini API** (gói `google-genai`, gói miễn phí, key lấy ở Google AI Studio) mà harness và nghiệp vụ không phải sửa.
- Mọi lỗi của AI tới tay người dùng ở dạng `{code, message_vi, retryable}`, không lộ key hay nội dung lỗi gốc.
- Giới hạn số lần gọi AI mỗi ngày (`DAILY_AI_LIMIT`).
- Mốc 2. Liên quan AC08 (JSON lỗi chỉ sửa 1 lần; timeout hoặc key sai không làm mất câu nhập).

## Các file
| File | Vai trò |
|---|---|
| `app/providers/gemini_provider.py` | `GeminiProvider`: gọi `models.generate_content`, lọc schema, đổi lỗi SDK thành `ProviderError` |
| `app/providers/errors.py` | `ProviderError(code)` và bảng 10 mã `ai_*` kèm `message_vi` và `retryable` |
| `app/providers/ai_provider.py` | Thêm `response_schema`, `provider_name`, `model_name` |
| `app/dependencies.py` | `create_provider(settings)`: chọn provider theo `AI_PROVIDER`; `get_daily_ai_limit()` |
| `app/models/ai_run.py` + migration `2ee8aebf5926` | Bảng `ai_runs`: mỗi tác vụ AI một dòng, chỉ lưu metadata |
| `app/repositories/ai_run_repository.py` | `add_run`, `count_calls_today(timezone)` |
| `tests/conftest.py` | Chặn mọi lần tạo client Gemini thật trong test |
| `tests/unit/test_gemini_provider.py` | Thay client bằng bản giả, giả lập từng loại lỗi |
| `tests/live/test_gemini_smoke.py` | Gọi thật tối đa 3 lần, chỉ chạy khi có `RUN_LIVE_AI=1` |
| `tests/integration/test_ai_runs.py` | Ghi `ai_runs`, đếm theo ngày và múi giờ, chặn khi hết hạn mức |

## Khái niệm

### `generate_content`: gọi API không trạng thái (stateless)
Mỗi lần gọi phải gửi **toàn bộ** ngữ cảnh; Google không nhớ gì giữa các lần gọi. Lịch sử hội thoại nằm trong Postgres của mình.
```python
client.models.generate_content(
    model=settings.gemini_model,  # đọc từ .env, không hardcode
    contents=[
        types.Content(role="user", parts=[types.Part.from_text(text="...")]),
        types.Content(role="model", parts=[...]),
    ],  # Gemini gọi phía AI là "model"
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,  # luật, tách khỏi lời người dùng
        max_output_tokens=800,  # tính cả token "suy nghĩ"
        response_mime_type="application/json",
        response_json_schema=cleaned_schema,  # structured output
        http_options=types.HttpOptions(timeout=30_000),  # đơn vị: mili giây
    ),
)
```
| | Kiểu "messages" (OpenAI, Anthropic) | Gemini |
|---|---|---|
| Vai AI | `assistant` | `model` |
| System prompt | tham số `system` | `config.system_instruction` |
| JSON theo schema | tùy nhà cung cấp | `response_mime_type` + `response_json_schema` |

### Structured output vẫn phải validate
Gemini cam kết JSON **đúng cú pháp**, nhưng nội dung vẫn có thể sai, hoặc bị cắt giữa chừng khi hết token. Vì vậy harness vẫn kiểm tra bằng Pydantic và vẫn sửa 1 lần.

Gemini cũng **không hỗ trợ** một số từ khóa JSON Schema, ví dụ `minLength` và `default`. Hàm `to_gemini_schema` lọc các từ khóa này trước khi gửi; Pydantic phía mình vẫn kiểm tra đầy đủ.

### Vì sao phải phân loại lỗi
| Lỗi | Phản ứng đúng |
|---|---|
| Key sai hoặc thiếu (400/401/403) | `ai_auth_failed`, không thử lại |
| Timeout, 5xx, lỗi mạng | Cho phép thử lại (`retryable: true`) |
| 429 theo phút | `ai_rate_limited`, đợi rồi thử lại |
| 429 theo ngày | `ai_quota_exhausted`, không thử lại trong ngày |
| Bị chặn bởi bộ lọc an toàn | `ai_blocked`, gợi ý diễn đạt khác |

SDK **mặc định không retry**, và dự án giữ nguyên như vậy: tự retry liên tục khi bị 429 chỉ làm bị chặn lâu hơn.

### Dependency injection để test không gọi mạng
`GeminiProvider(client=FakeClient(...))`: test truyền một client giả vào. `tests/conftest.py` còn thay `google.genai.Client` bằng một hàm luôn ném lỗi, nên dù test có lỡ tạo client thật thì cũng thất bại ngay, không gọi API.

### Đếm "hôm nay" theo múi giờ bằng Postgres
```python
local_day = cast(func.timezone(timezone, AiRun.created_at), Date)
today = cast(func.timezone(timezone, func.now()), Date)
```
`timezone('Asia/Ho_Chi_Minh', created_at)` đổi giờ UTC sang giờ Việt Nam ngay trong Postgres, nên Python trên Windows không cần thêm thư viện `tzdata`.

## Luồng của một lượt chat với `ai_runs`
```
gửi tin ─► đã có request_id và đã xong? ─► trả lại kết quả cũ (không tính lượt)
        └► kiểm tra hạn mức: tổng call_count hôm nay ≥ DAILY_AI_LIMIT? ─► 429 daily_limit_reached
        └► tx1: lưu câu (pending) ─► harness (1–2 lần gọi) ─► tx2: reply + corrections + 1 dòng ai_runs
```
Provider `fake` không bị đếm và không bao giờ bị chặn.

## Quyết định và lý do
| Quyết định | Lý do |
|---|---|
| `generate_content` thay vì Interactions API | Không giữ trạng thái trên server Google; lịch sử nằm trong DB của mình |
| `GEMINI_THINKING_LEVEL=minimal` | Token "suy nghĩ" bị tính vào `max_output_tokens`; mức thấp giúp JSON không bị cắt |
| Hạn mức tính theo **số lần gọi**, kể cả lần gọi sửa JSON | Đúng với hạn mức thật phía Google |
| Lưu `ai_runs` trong DB, không đếm trong bộ nhớ | Vẫn đúng sau khi khởi động lại app |

## Cách chạy và tự test
```powershell
pytest tests/unit/test_gemini_provider.py -v
pytest tests/integration/test_ai_runs.py -v
$env:RUN_LIVE_AI="1"; pytest tests/live -s     # gọi Gemini thật 3 lần, chỉ khi cần
```

## Lỗi đã gặp
| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `node --test tests/js/` báo lỗi | Node 22 coi đường dẫn thư mục là một file | Dùng glob: `"tests/js/**/*.test.mjs"` |
| Không phân biệt được 429 theo ngày hay theo phút | Tài liệu Google không nói | Tạm đoán dựa vào chữ `PerDay` trong `details`; ghi vào `progress.md` để xác nhận sau |
| Key sai trả 400 chứ không phải 401 | Smoke test cho thấy `400 INVALID_ARGUMENT` | Xử lý cả 400 có chữ "API key", 401 và 403 |
