# 05. Trang chat: Jinja2 render phía server + JavaScript `fetch`

## Mục tiêu

Trang chat tiếng Việt, không React:
- Thanh bên "Hội thoại" (Từ vựng, Ôn tập, Cài đặt hiện mờ, "sắp có").
- Vùng tin nhắn, ô nhập, nút Gửi.
- Tạo cuộc trò chuyện mới, mở lại cuộc cũ; lịch sử còn sau khi restart app.
- Khi gửi: hiện "Đang xử lý…" ngay, không gửi trùng, hiện reply; lỗi thì báo tiếng Việt và giữ câu đã nhập.
- Escape mọi nội dung (chống XSS).

Liên quan:
- **FR01**: chọn chủ đề, trình độ, cách sửa; trạng thái gửi rõ ràng; không tạo hai lượt; tiếp tục đúng hội thoại.
- **Yêu cầu phi chức năng**: loading dưới 300 ms (đo được 6 ms); escape nội dung; dữ liệu còn sau restart.
- **Mục tiêu Mốc 1** ("chat giả lập; lịch sử còn sau restart") đã đạt.

## Các file

| File | Vai trò |
|---|---|
| `app/routers/pages.py` | `GET /` (chuyển tới hội thoại mới nhất hoặc màn hình chào), `GET /conversations/{id}`; gắn header bảo mật |
| `app/templates/base.html` | Khung HTML chung: `<head>`, CSS, các `block` |
| `app/templates/chat.html` | Thanh bên, vùng tin nhắn, ô nhập, hộp thoại tạo hội thoại |
| `app/templates/_macros.html` | Macro `render_turn`: HTML cho một lượt (câu user, thẻ sửa, reply) |
| `app/templates/not_found.html` | Trang 404 tiếng Việt |
| `app/static/js/chat.js` | Gửi tin và tạo hội thoại bằng `fetch`; vẽ lượt mới bằng `textContent` |
| `app/static/css/chat.css` | Giao diện; màn hình nhỏ thì thanh bên chuyển lên trên |
| `app/main.py` | Mount `/static`, gắn router trang |
| `app/repositories/conversation_repository.py` | Thêm `list_conversations`, `list_messages` (kèm `selectinload`) |
| `app/services/conversation_service.py` | Thêm `list_conversations`, `get_history`, `group_turns` |
| `app/schemas/conversation.py` | Thêm `ConversationSummary`, `TurnView`, `ConversationHistory` |
| `tests/integration/test_pages.py` | 9 test cho trang |

## Khái niệm

### Jinja2: render phía server (SSR)
Server dùng dữ liệu trong DB để ghép ra HTML hoàn chỉnh rồi mới gửi cho trình duyệt.
```python
# pages.py
return templates.TemplateResponse(request, "chat.html", {"conversation": history, ...})
```
```html
<!-- chat.html -->
{% for turn in conversation.turns %}
  {{ render_turn(turn) }}
{% endfor %}
```
- `{{ x }}`: in giá trị, **tự động escape**. `<script>` thành `&lt;script&gt;`, trình duyệt hiện như chữ.
- `{% for %}`, `{% if %}`: vòng lặp, điều kiện.
- `{% extends "base.html" %}` + `{% block body %}`: **kế thừa template**. Trang con chỉ điền phần riêng, khung chung viết một lần.
- `{% macro render_turn(turn) %}`: "hàm" sinh HTML, dùng lại nhiều lần; `{% from "_macros.html" import render_turn %}` để nhập.
- `url_for('static', path='js/chat.js')`: sinh đường dẫn tới file tĩnh.

Lợi ích: mở lại hội thoại hay restart app thì chỉ cần tải trang, server đọc DB và render lại. JS không phải lo tải lịch sử.

### `fetch` phía JS
Hàm có sẵn trong trình duyệt để gửi HTTP mà **không tải lại trang**. Nó chạy bất đồng bộ: `await` chờ kết quả, nhưng trang không bị đơ.
```js
const response = await fetch(`/api/conversations/${id}/messages`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ request_id, text, input_mode: "text" }),
});
const data = await response.json();
```
- `response.ok`: `true` khi mã HTTP là 2xx.
- `fetch` chỉ **ném lỗi** khi mất mạng; lỗi 4xx/5xx vẫn trả `response` bình thường. Vì vậy code xử lý hai đường riêng: `if (!ok)` và `catch`.

### Phân công: server render, JS chỉ làm phần động
| Việc | Ai làm |
|---|---|
| Danh sách hội thoại, lịch sử khi mở trang | Jinja2 (server) |
| Gửi tin, hiện lượt mới không tải lại trang | `chat.js` |
| Tạo hội thoại | `chat.js` gọi `POST /api/conversations` rồi chuyển trang |

Đánh đổi: HTML của một lượt được viết ở 2 nơi (`_macros.html` và `renderTurn` trong JS). Sửa một bên thì phải sửa bên kia; comment ở đầu mỗi bên đã nhắc điều này.

### Ba lớp chống XSS
XSS là khi kẻ xấu chèn được `<script>` vào trang và trình duyệt chạy nó.
1. **Jinja2 autoescape**: mọi `{{ }}` đều được escape.
2. **JS chỉ dùng `textContent` / `createElement`**, không bao giờ `innerHTML` với dữ liệu:
   ```js
   node.textContent = data.reply.text;   // an toàn: luôn là chữ
   // node.innerHTML = data.reply.text;  // CẤM: chuỗi có <img onerror=...> sẽ chạy
   ```
3. **Header `Content-Security-Policy: default-src 'self'`**: trình duyệt chỉ chạy script và CSS lấy từ chính app, cấm script inline. Kể cả khi có chỗ quên escape, script chèn vào cũng không chạy. Vì vậy mọi JS và CSS đều nằm trong file riêng ở `static/`.

Dữ liệu truyền cho JS qua thuộc tính `data-` (đã escape), không nhúng vào `<script>`:
```html
<form id="message-form" data-conversation-id="{{ conversation.id }}">
```
```js
const conversationId = form.dataset.conversationId;
```

### Luồng gửi tin trong `chat.js`
```
bấm Gửi / Enter
 ├─ đang gửi? → bỏ qua (chặn bấm 2 lần)
 ├─ text.trim() rỗng? → "Bạn chưa nhập nội dung.", không gọi server
 ├─ request_id = (lần trước lỗi và cùng câu) ? id cũ : crypto.randomUUID()
 ├─ [đồng bộ] khóa nút + ô nhập, "Đang xử lý…", chèn câu tạm   ← hiện sau ~6 ms
 ├─ await fetch(...)
 │   ├─ succeeded → thay câu tạm bằng lượt thật, xóa ô nhập
 │   ├─ failed / 4xx / 5xx → gỡ câu tạm, hiện message_vi, GIỮ chữ trong ô nhập
 │   └─ mất mạng (catch) → "Không kết nối được máy chủ…", giữ chữ
 └─ finally → mở khóa nút
```
- Dùng lại `request_id` khi gửi lại đúng câu đã lỗi: server nhận ra đó là cùng một lượt (idempotency, bài 04).
- `event.isComposing`: không gửi khi bộ gõ tiếng Việt còn đang ghép chữ.

### `selectinload`: tránh vấn đề N+1
Đọc 20 tin nhắn, rồi với mỗi tin lại truy vấn riêng corrections của nó, là 1 + 20 truy vấn (gọi là "N+1"). `selectinload(Message.corrections)` tải corrections của **tất cả** tin nhắn bằng 1 truy vấn thêm (`WHERE message_id IN (...)`).

### `<dialog>` của HTML
Hộp thoại có sẵn trong trình duyệt: `dialog.showModal()` mở, phím Escape tự đóng, focus bị giữ bên trong hộp thoại. JS thêm hành vi bấm ra ngoài thì đóng (theo spec).

## Quyết định và lý do

| Quyết định | Lý do |
|---|---|
| Server render (phương án A), không dựng hết bằng JS | Đúng hướng "Jinja2 + JS nhỏ"; lịch sử sau restart có sẵn; escape tự động; ít JS |
| Thêm header CSP, chỉ cho trang HTML | Lớp chống XSS thứ ba. Không gắn cho `/docs` vì Swagger cần tải script từ CDN |
| `GET /` chuyển hướng `303` tới hội thoại mới nhất | Mở app là tiếp tục ngay buổi gần nhất |
| Thẻ sửa dùng `<details open>` | Thu gọn được (theo bố cục spec) mà không cần JS |
| Thẻ sửa luôn hiện, kể cả chế độ giao tiếp | Nút "Xem lỗi" chưa có; ẩn theo chế độ (AC04) làm sau |
| Chưa hiện giờ gửi | Đổi sang múi giờ của profile trên Windows cần thêm thư viện `tzdata` |

## Cách chạy và tự test

```powershell
docker compose up -d db
.venv\Scripts\activate
uvicorn app.main:app --reload
```
Mở `http://127.0.0.1:8000/`.

Tự kiểm tra từng yêu cầu:
1. **Tạo hội thoại**: bấm "+ Cuộc trò chuyện mới". Để trống chủ đề rồi bấm "Bắt đầu" thì thấy báo lỗi. Nhập chủ đề, chọn trình độ, bấm "Bắt đầu" thì trang chuyển sang hội thoại mới.
2. **Gửi tin**: gõ `Yesterday I go to work.` rồi nhấn Enter. Thấy reply và thẻ "Gợi ý sửa".
3. **Trạng thái đang xử lý**: F12 → tab Network → chọn throttling "Slow 3G", rồi gửi. Thấy "Đang xử lý…", nút Gửi bị mờ; bấm liên tục cũng chỉ có 1 request trong tab Network.
4. **Lỗi**: tắt uvicorn (Ctrl+C) rồi gửi. Thấy "Không kết nối được máy chủ…" và câu vẫn còn trong ô nhập. Bật lại uvicorn, gửi lại: thành công, chỉ có một lượt.
5. **XSS**: gửi `<img src=x onerror=alert(1)>`. Thấy chuỗi đó hiện dạng chữ, không có hộp alert.
6. **Restart**: Ctrl+C uvicorn, chạy lại, tải trang: lịch sử còn nguyên.
7. **Màn hình nhỏ**: F12 → bật chế độ thiết bị (Ctrl+Shift+M). Thanh bên chuyển lên trên, ô nhập vẫn thấy.

Chạy test:
```powershell
pytest tests/integration/test_pages.py -v
```

## Đã kiểm tra trên trình duyệt thật (Playwright)
| Kiểm tra | Kết quả |
|---|---|
| "Đang xử lý…" sau khi bấm | 6 ms; nút bị khóa, ô nhập chỉ đọc |
| Bấm Gửi lần 2 + Enter khi đang gửi | Chỉ 1 request |
| Server trả `failed` | Hiện `message_vi`, câu vẫn trong ô nhập |
| Mất mạng, gửi lại cùng câu | Báo lỗi tiếng Việt; **cùng `request_id`** ở lần gửi lại |
| Câu chỉ có khoảng trắng | Báo lỗi, không gửi request |
| Chủ đề `<img onerror=...>`, câu `<script>...` | Hiện dạng chữ, không chạy |
| Restart uvicorn | `/` mở hội thoại mới nhất, lịch sử còn đủ |
| Bấm hội thoại cũ ở thanh bên | Mở đúng, mục đó được tô đậm |

## Lỗi đã gặp

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| Console báo 404 `favicon.ico` | Trình duyệt tự xin biểu tượng tab, app chưa có | Vô hại; đã ghi vào "Ý tưởng sau" |
| Fake provider sửa câu đúng `I am tester.` thành "I go → I went" | FakeProvider luôn trả cùng một correction | Đúng thiết kế của fake; Claude thật ở Mốc 2 sẽ sửa theo câu thật |
