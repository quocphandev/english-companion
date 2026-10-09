# 04. API hội thoại: router, service, repository, transaction và idempotency

## Mục tiêu

Hai endpoint đầu tiên có nghiệp vụ thật, chạy với fake provider:
- `POST /api/conversations`: tạo hội thoại, trả `conversation_id`.
- `POST /api/conversations/{id}/messages`: gửi một câu, nhận reply và corrections.

Theo đúng luồng SPEC mục 7: validate → lưu lượt pending → build context → harness → validate → ghi reply + corrections trong **một transaction**.

- Mốc 1. **FR01**: chọn topic, level, chế độ sửa; giữ nguyên câu gốc; trạng thái gửi rõ ràng; lịch sử theo đúng hội thoại.
- **AC01 đạt**: câu rỗng hoặc quá 2.000 ký tự bị chặn; gửi hai lần cùng `request_id` chỉ có một lượt.
- **AC08 một phần**: AI lỗi thì câu nhập vẫn còn trong DB và thử lại được.

## Các file

| Tầng | File | Vai trò |
|---|---|---|
| Router | `app/routers/conversations.py` | Nhận HTTP, để Pydantic validate, gọi service, trả kết quả. Không có nghiệp vụ |
| DI | `app/dependencies.py` | `get_harness()`, `get_conversation_service()`: lắp ráp object cho mỗi request |
| Service | `app/services/conversation_service.py` | Nghiệp vụ: 2 transaction, idempotency, thử lại lượt lỗi |
| Repository | `app/repositories/conversation_repository.py` | Mọi câu truy vấn DB. Chỉ `add`/`flush`, không `commit` |
| Schema | `app/schemas/conversation.py` | Request/response; validator `empty_message`, `message_too_long` |
| Schema | `app/schemas/error.py` | `ErrorBody {code, message_vi, retryable}` |
| Lỗi | `app/errors.py` | `AppError` và các handler đổi mọi lỗi sang `ErrorBody` |
| Model | `app/models/correction.py`; sửa `message.py` | Bảng `corrections`; cột `messages.reply_to_message_id` |
| Migration | `alembic/versions/..._add_corrections_and_message_reply_link.py` | Migration thứ 2 (`9ba16f575a07`) |
| App | `app/main.py` | Gắn router và handler lỗi |
| Test | `tests/fakes.py` | `ScriptedProvider`, `RecordingFakeProvider` dùng chung |
| Test | `tests/integration/conftest.py` | Thêm fixture `client`, `use_provider` |
| Test | `tests/integration/test_conversations_api.py` | 19 test cho API |

## Kiến trúc: ai làm gì

```
HTTP request
  │
  ▼  routers/conversations.py   "người tiếp tân": nhận, kiểm tra hình thức, chuyển tiếp
  ▼  services/conversation_service.py   "người quản lý": quyết định, mở/đóng transaction
  ├──▶ repositories/conversation_repository.py   "thủ kho": đọc/ghi DB
  └──▶ harness/chat_harness.py   "phiên dịch viên": nói chuyện với AI
```
Phụ thuộc chỉ đi một chiều xuống dưới. Router không chạm DB, repository không biết HTTP. Nhờ vậy mỗi tầng test và thay thế được riêng.

## Khái niệm

### Transaction trong một lượt chat
Bài 02 đã giới thiệu transaction. Ở đây có hai quy tắc áp dụng:

1. **Reply và corrections ghi chung một transaction.** Nếu ghi correction lỗi thì reply cũng không được lưu; DB không bao giờ "có reply mà thiếu correction".
2. **Không giữ transaction trong lúc chờ AI.** Gọi AI có thể mất tới 30 giây; giữ transaction lâu sẽ chiếm kết nối và khóa dữ liệu. Vì vậy chia thành 2 transaction ngắn:

```
tx1: INSERT câu user (status=pending)          → COMMIT   ← câu nhập đã an toàn
     gọi harness (không có transaction nào mở)
tx2: INSERT reply + corrections, user→succeeded → COMMIT
     (hoặc user→failed nếu AI lỗi)
```
Trong code:
```python
message = self._repository.add_user_message(...)  # add + flush
self._session.commit()  # kết thúc tx1
result = self._harness.run_turn(context)  # chờ AI
self._repository.add_reply(user_message, result.reply, PROMPT_VERSION)
self._session.commit()  # kết thúc tx2
```
Repository chỉ `flush` (gửi SQL), còn **service** mới `commit`. Lý do: chỉ service biết những thao tác nào phải đi chung một nhóm.

### Idempotency
Một thao tác là idempotent nếu gọi 1 lần hay n lần thì kết quả vẫn như nhau. Ví dụ đời thường: bấm nút thang máy 5 lần thì thang vẫn chỉ đến một lần.

Ở đây: client sinh `request_id` (ví dụ UUID) cho mỗi câu và gửi lại đúng id đó khi thử lại.

| Lượt cũ với `request_id` này | Server làm gì |
|---|---|
| Chưa có | Tạo lượt mới |
| `succeeded` | Trả kết quả đã lưu, **không gọi AI** (không tốn phí) |
| `pending` | Trả `status: pending` (request trước chưa xong) |
| `failed` | Gọi AI lại **trên chính câu đó**, không tạo câu mới |
| Khác hội thoại hoặc khác nội dung | `409 request_id_conflict` |

**Hai request cùng lúc:** cả hai cùng tìm và cùng thấy "chưa có", rồi cùng INSERT. Ràng buộc `UNIQUE(request_id)` trong DB chặn bản thứ hai bằng `IntegrityError`; service bắt lỗi đó, `rollback`, rồi đọc lượt đã có.
```python
try:
    message = self._repository.add_user_message(...)
    self._session.commit()
except IntegrityError:
    self._session.rollback()
    existing = self._repository.find_message_by_request_id(request.request_id)
```
Chốt chặn thật sự là **ràng buộc trong DB**, không phải câu `if` trong code. Câu `if` có thể bị hai request vượt qua cùng lúc; UNIQUE thì không.

### Dependency của FastAPI (`Depends`)
FastAPI tự gọi các hàm phụ thuộc rồi truyền kết quả vào endpoint:
```python
def get_conversation_service(
    session: Annotated[Session, Depends(get_session)],
    harness: Annotated[ChatHarness, Depends(get_harness)],
) -> ConversationService: ...


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]


def send_message(
    conversation_id: int, body: SendMessageRequest, service: ConversationServiceDep
): ...
```
`Annotated[Kiểu, Depends(hàm)]` nghĩa là: "biến này có kiểu X, lấy giá trị bằng cách gọi hàm Y".
Trong test thay bằng: `app.dependency_overrides[get_harness] = lambda: ChatHarness(ScriptedProvider(...), 800)`.

### Exception handler
Thay vì `try/except` ở từng endpoint, đăng ký một lần ở app:
```python
app.add_exception_handler(AppError, handle_app_error)  # lỗi nghiệp vụ dự kiến
app.add_exception_handler(RequestValidationError, handle_validation_error)  # 422
app.add_exception_handler(
    Exception, handle_unexpected_error
)  # 500, không lộ stack trace
```
Service chỉ cần `raise conversation_not_found()`; handler đổi nó thành `404 {code, message_vi, retryable}`.

### Validator tự đặt mã lỗi
```python
@field_validator("text")
@classmethod
def check_text(cls, value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("empty_message", "Message must not be empty")
    ...
    return value  # trả bản GỐC, không strip: spec yêu cầu lưu nguyên văn
```
`PydanticCustomError("empty_message", ...)` làm cho lỗi có `type = "empty_message"`. Handler đọc type đó để trả đúng `code` cho UI.

### `monkeypatch` (pytest)
Tạm thay một hàm hoặc thuộc tính trong lúc chạy một test, hết test tự trả lại như cũ. Test "hai request cùng lúc" dùng nó để giả lập lần tìm đầu tiên "không thấy".

## Quyết định và lý do

| Quyết định | Lý do |
|---|---|
| `level`, `correction_mode` ghi đè vào **profile** khi tạo hội thoại (không thêm cột vào `conversations`) | Chủ dự án chọn: đúng bảng spec. Hệ quả: đổi cài đặt ở hội thoại mới thì hội thoại cũ cũng dùng cài đặt mới |
| Một profile mặc định (get-or-create) | App local một người, chưa có đăng nhập |
| AI lỗi trả `200` + `status: failed` + `error` | Lượt thất bại là kết quả hợp lệ; body vẫn có câu user để UI hiện nút thử lại |
| Cột `reply_to_message_id` (UNIQUE) | Nối reply với câu user, để gửi trùng id thì trả đúng reply; mỗi câu tối đa một reply |
| Corrections gắn vào **câu user** | Correction nhận xét câu người học viết |
| Context chỉ lấy tin `succeeded` của đúng hội thoại, tối đa 20 | FR01: hội thoại mới không mang lịch sử cũ; câu lỗi không làm nhiễu AI |
| Harness ném exception thì đánh dấu `failed` + `ai_unavailable` | Câu không bị kẹt ở `pending` mãi, vẫn thử lại được |
| `request_id`: 1–64 ký tự `A-Z a-z 0-9 - _` | Đủ cho UUID; chặn ký tự lạ |

## API

```http
POST /api/conversations
{"topic": "work", "level": "A2", "correction_mode": "learning"}
→ 201 {"conversation_id": 1}

POST /api/conversations/1/messages
{"request_id": "c0ffee-1", "text": "Yesterday I go to work.", "input_mode": "text"}
→ 200 {"status": "succeeded",
       "message": {"id": 1, "role": "user", "text": "...", "status": "succeeded", "created_at": "...Z"},
       "reply":   {"id": 2, "role": "assistant", "text": "That sounds nice! ...", ...},
       "corrections": [{"category": "grammar", "original_span": "I go", "corrected_text": "I went", "explanation_vi": "..."}],
       "error": null}
```
| Tình huống | HTTP | `code` |
|---|---|---|
| Câu rỗng / chỉ khoảng trắng | 422 | `empty_message` |
| Quá 2.000 ký tự | 422 | `message_too_long` |
| Dữ liệu sai khác | 422 | `invalid_input` |
| Không có hội thoại | 404 | `conversation_not_found` |
| `request_id` đã dùng cho câu khác | 409 | `request_id_conflict` |
| AI trả JSON hỏng 2 lần | 200, `status: failed` | `invalid_ai_output` (retryable) |
| Provider ném lỗi | 200, `status: failed` | `ai_unavailable` (retryable) |
| `AI_PROVIDER` khác `fake` | 503 | `provider_not_supported` |

## Cách chạy và tự test

```powershell
docker compose up -d db
.venv\Scripts\activate
alembic upgrade head                 # lên 9ba16f575a07
pytest tests/integration/test_conversations_api.py -v
uvicorn app.main:app --reload
```
Mở `http://127.0.0.1:8000/docs`, chọn **POST /api/conversations** → *Try it out* → gửi `{"topic": "work"}`. Sau đó dùng `conversation_id` nhận được để gửi tin ở endpoint thứ hai.

Những thứ nên thử trên `/docs`:
1. Gửi một câu, rồi gửi **lại đúng body đó**: response giống hệt, DB không thêm dòng mới.
2. Giữ `request_id` nhưng đổi `text`: nhận `409`.
3. `text` là `"   "`: nhận `422 empty_message`.
4. Restart uvicorn, gửi lại `request_id` cũ: vẫn trả kết quả cũ, vì dữ liệu nằm trong DB.

Xem dữ liệu thật:
```powershell
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select id, role, status, request_id, reply_to_message_id from messages order by id"'
```

Thử làm test đỏ: trong `conversation_service.py`, xóa khối `except IntegrityError:` (chỉ giữ phần `try`). Chạy test, `test_concurrent_duplicate_is_caught_by_unique_constraint` sẽ fail với `IntegrityError`. Nhớ hoàn tác.

## Lỗi đã gặp

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `ruff format .` sửa cả file `docs/learning/*.md` | ruff 0.16 định dạng luôn code Python nằm trong Markdown | Không phải lỗi; chỉ đổi cách xuống dòng trong khối code |

## Chưa làm (đã ghi `progress.md`)
Câu hỏi mở đầu khi tạo hội thoại (FR01); lượt `pending` bị kẹt nếu server sập giữa chừng; lưu `suggested_words`; ẩn thẻ lỗi ở chế độ giao tiếp (AC04, phần UI); đưa giới hạn 2.000 ký tự vào Settings; API đọc lịch sử hội thoại.
