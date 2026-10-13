# 17. Deploy bản demo public: mật khẩu chung, rate limit, Render + Neon

## Mục tiêu
Chủ dự án muốn có link công khai để người khác thử app (chọn phương án B: link cố định, có HTTPS). Đây không phải một FR trong SPEC. Trước khi mở app ra Internet, cần chặn ba rủi ro:
1. Người lạ dùng key Gemini của bạn. Chặn bằng **mật khẩu chung** và **rate limit**, cộng với `DAILY_AI_LIMIT` đã có từ trước.
2. App chỉ có một hồ sơ, nên một người bấm "Xóa toàn bộ" là xóa luôn dữ liệu của mọi người. Chặn bằng **chế độ demo**: tắt mọi chức năng xóa.
3. Người khác nghe lén mật khẩu trên đường truyền. Render cấp **HTTPS** sẵn nên rủi ro này được xử lý.

## File đã tạo/sửa
| File | Vai trò |
|---|---|
| `app/security.py` | Middleware kiểm tra mật khẩu (HTTP Basic) và giới hạn số lần gọi AI mỗi phút theo IP |
| `app/config.py` | Biến `APP_PASSWORD`, `RATE_LIMIT_PER_MINUTE`, `PUBLIC_DEMO`. App từ chối khởi động nếu bật demo mà không có mật khẩu. Tự đổi `postgresql://` thành `postgresql+psycopg://` |
| `app/main.py` | Gọi `install_security(app, settings)` |
| `app/services/data_service.py`, `app/dependencies.py` | `allow_delete=False` khi `PUBLIC_DEMO` thì xóa trả 403 `deleting_disabled` |
| `app/routers/pages.py`, `templates/chat.html`, `templates/settings.html` | Ẩn nút 🗑 và form "Xóa toàn bộ" ở bản demo |
| `Dockerfile` | Python 3.13, cài từ `requirements.lock.txt`, chạy migration khi khởi động, cổng lấy từ `$PORT`, thêm `--proxy-headers`. Sửa lỗi `adduser` |
| `render.yaml` | Khai báo service trên Render bằng code (Blueprint) |
| `.env.example`, `README.md` | Biến mới; hướng dẫn deploy từng bước |
| `tests/unit/test_security.py`, `tests/integration/test_data_controls.py` | Test mật khẩu, rate limit, chuẩn hóa URL, chế độ demo |

## Khái niệm mới

### Middleware
Middleware là một lớp bọc quanh toàn bộ app. Mọi request đi qua nó **trước khi** đến router, nên đây là chỗ hợp lý cho những việc áp dụng cho mọi trang, như kiểm tra mật khẩu:
```python
async def __call__(self, scope, receive, send):
    if not password_ok(scope):
        await JSONResponse(..., status_code=401)(scope, receive, send)  # dừng ở đây
        return
    await self.app(scope, receive, send)  # cho đi tiếp vào app
```
`SecurityMiddleware` viết theo kiểu ASGI thuần, tức là nhận `scope, receive, send`. Cách này đơn giản và không ảnh hưởng tới các route khác.

### HTTP Basic Auth
Khi server trả về `401` kèm header `WWW-Authenticate: Basic`, trình duyệt tự hiện hộp nhập tên và mật khẩu. Sau đó, mọi request tới cùng trang web, kể cả `fetch` trong JS, đều được gửi kèm header `Authorization: Basic base64(tên:mật_khẩu)`. Base64 **không phải mã hóa**, ai đọc được header là biết mật khẩu, nên chỉ dùng được khi có HTTPS. Khi so mật khẩu, code dùng `secrets.compare_digest`. Hàm này mất cùng một khoảng thời gian dù sai ở ký tự đầu hay ký tự cuối, nên kẻ tấn công không đoán dần mật khẩu bằng cách đo thời gian phản hồi được.

### Rate limit kiểu cửa sổ trượt (sliding window)
Với mỗi IP, server giữ danh sách thời điểm của các lần gọi trong 60 giây gần nhất. Lần gọi mới bị từ chối (429 `rate_limited`) khi danh sách đã đủ N phần tử:
```python
limiter = SlidingWindowLimiter(limit=2)
limiter.allow("1.2.3.4")  # True
limiter.allow("1.2.3.4")  # True
limiter.allow("1.2.3.4")  # False: đợi lần gọi cũ nhất quá 60 giây
```
Chỉ các endpoint có thể gọi AI mới bị đếm: gửi tin, kết thúc buổi, trợ giúp, tra từ. Bộ đếm nằm trong bộ nhớ. Cách này đủ vì bản free chỉ chạy một instance, và restart thì bộ đếm về 0. Để không ai lách được, hạn mức chi phí thật vẫn là `DAILY_AI_LIMIT`, vì giá trị này lưu trong DB.

### Reverse proxy và `--proxy-headers`
Trên Render, người dùng không kết nối thẳng vào app mà đi qua proxy HTTPS của Render. Vì vậy app chỉ thấy IP của proxy. Proxy ghi IP thật vào header `X-Forwarded-For`. Cờ `--proxy-headers` bảo uvicorn đọc header này, nhờ đó rate limit đếm theo đúng người dùng.

### Infrastructure as code (`render.yaml`)
Thay vì bấm từng ô trên web, cấu hình service được viết thành file trong repo. Đọc file là biết server chạy thế nào, sửa cấu hình thì có lịch sử trong Git. Secret khai báo `sync: false`: Render hỏi giá trị lúc tạo service, còn file không chứa secret.

## Luồng chạy trên Render
1. Bạn push lên `master`. Render build image từ `Dockerfile`.
2. Container khởi động: `alembic upgrade head` tạo hoặc cập nhật bảng trên Neon, sau đó chạy `uvicorn` ở cổng `$PORT`.
3. Render gọi `/health` để biết app đã sẵn sàng. Route này không cần mật khẩu.
4. Người dùng mở link. Middleware trả 401, trình duyệt hỏi mật khẩu. Nhập đúng thì app chạy như ở máy.

## Quyết định và lý do
- **Basic Auth thay vì trang đăng nhập.** Không cần thêm bảng user, session hay thư viện nào. Đổi lại giao diện xấu hơn và không có nút đăng xuất. Đăng nhập theo từng người dùng là một tính năng lớn, vẫn nằm ngoài phạm vi.
- **Neon thay vì Postgres của Render.** Postgres free của Render bị xóa sau 30 ngày, còn Neon free giữ dữ liệu lâu dài.
- **Migration chạy trong lệnh khởi động.** Bản free của Render không có bước "pre-deploy". `alembic upgrade head` chạy nhiều lần vẫn an toàn: đã ở bản mới nhất thì nó không làm gì.
- **Dockerfile chuyển sang Python 3.13 và file lock**, để trên server dùng đúng bộ thư viện đã chạy test trên máy.
- **Bật demo mà thiếu mật khẩu thì app từ chối khởi động**, thay vì lặng lẽ chạy công khai mà không có bảo vệ.

## Cách chạy và tự test
```bash
pytest tests/unit/test_security.py tests/integration/test_data_controls.py -q
```
Đã thử bằng container thật, cấu hình giống Render nhưng dùng AI giả và một DB trống tên `english_companion_deploycheck`:
- Migration chạy từ DB trống đến bản mới nhất.
- `/health` trả 200. Không có mật khẩu hoặc sai mật khẩu thì 401, đúng mật khẩu thì 200.
- Với `RATE_LIMIT_PER_MINUTE=3`: 3 tin đầu được gửi, tin thứ 4 bị 429. Trên trình duyệt hiện "Bạn gửi quá nhanh…".
- Xóa hội thoại trả 403 `deleting_disabled`. Nút 🗑 và form "Xóa toàn bộ" không còn hiện.

## Lỗi đã gặp
- **`adduser --create-home` báo "Unknown option".** Image `python:*-slim` mới dựa trên Debian 13, lệnh `adduser` ở đó không có tùy chọn này. Trước giờ chưa ai build image nên lỗi chưa lộ ra. Đã đổi sang `useradd --create-home`.
- **Test bị lỗi `got multiple values for keyword argument 'database_url'`.** Hàm helper truyền `database_url` hai lần. Đã sửa bằng cách gộp vào một dict trước khi tạo `Settings`.
- **114 test integration báo lỗi** khi Docker Desktop chưa bật (không có Postgres). Đây không phải lỗi code: bật Docker xong thì toàn bộ test đạt.
- **Giới hạn đã biết:** `--forwarded-allow-ips='*'` tin mọi header `X-Forwarded-For`. Người dùng có thể giả header này để lách giới hạn theo phút. Họ vẫn phải có mật khẩu và vẫn bị `DAILY_AI_LIMIT` chặn.
