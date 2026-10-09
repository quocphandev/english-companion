# 01. Khung FastAPI, `/health` và cấu hình `.env`

## Mục tiêu

Dựng bộ khung nhỏ nhất chạy được: một web server có endpoint `GET /health` trả `{"status": "ok"}`, cấu hình đọc từ `.env` qua **một chỗ duy nhất**, và test đầu tiên.
Chưa có database, chưa có AI.

- Mốc: 1 (khung dự án). FR/AC: chưa ứng với FR nào, đây là nền cho mọi thứ sau.

## Các file

| File | Vai trò |
|---|---|
| `app/__init__.py` | File rỗng. Biến thư mục `app/` thành **package** để viết được `from app.config import ...` |
| `app/main.py` | Tạo object `app = FastAPI(...)` và khai báo `GET /health` |
| `app/config.py` | Class `Settings` đọc biến môi trường và `.env`; hàm `get_settings()` |
| `tests/integration/test_health.py` | Test gọi `/health`, kiểm tra mã 200 và body |
| `pyproject.toml` | Cấu hình pytest: `pythonpath = ["."]` để test import được `app` |

## Khái niệm

### Package và `__init__.py`
Python chỉ import được thư mục khi nó là package. File `__init__.py` (có thể rỗng) đánh dấu điều đó.
```python
from app.config import get_settings  # cần app/__init__.py
```

### venv (môi trường ảo)
Thư mục `.venv/` chứa một bản Python riêng và các thư viện của dự án, tách khỏi Python của máy.
Mỗi lần mở terminal mới phải bật: `.venv\Scripts\activate` (thấy `(.venv)` ở đầu dòng là đúng).

### Decorator
Decorator là cú pháp `@ten` đặt trên một hàm để "bọc" thêm hành vi cho hàm đó.
```python
@app.get("/health")  # đăng ký hàm này cho GET /health
async def health() -> dict[str, str]:
    return {"status": "ok"}  # FastAPI tự đổi dict thành JSON
```

### pydantic-settings
Bạn khai báo các thuộc tính có kiểu; thư viện tự đọc biến môi trường cùng tên (không phân biệt hoa thường) và ép kiểu.
```python
class Settings(BaseSettings):
    daily_ai_limit: int = 100  # đọc DAILY_AI_LIMIT, "100" -> 100
```
Nếu `.env` ghi `DAILY_AI_LIMIT=abc`, app báo lỗi ngay khi khởi động, không âm thầm chạy sai.
- `SecretStr` (dùng cho API key): khi in ra chỉ hiện `**********`, tránh lộ key vào log.
- `extra="ignore"`: bỏ qua biến không khai báo (ví dụ `POSTGRES_USER` chỉ dành cho Docker).

### `@lru_cache`
Decorator nhớ kết quả lần gọi đầu, các lần sau trả lại đúng object đó, nên `.env` chỉ đọc một lần.
```python
get_settings() is get_settings()  # True
```

### TestClient
`TestClient(app)` gửi request thẳng vào app trong bộ nhớ, không cần chạy uvicorn, không mở cổng mạng.
Test viết theo 3 bước: **chuẩn bị → gọi → kiểm tra (assert)**.

## Luồng chạy

```
uvicorn app.main:app  ->  import app/main.py  ->  lấy biến "app"
trình duyệt GET /health  ->  hàm health()  ->  {"status": "ok"}
```
`app.main:app` nghĩa là: module `app/main.py`, biến tên `app`.

## Quyết định và lý do

| Quyết định | Lý do |
|---|---|
| Cấu hình chỉ đọc qua `Settings` | Một chỗ duy nhất, có kiểu, lỗi sớm; không gọi `os.environ` rải rác |
| `pyproject.toml` với `pythonpath = ["."]` thay vì luôn gõ `python -m pytest` | Gõ `pytest` là chạy được, khỏi nhớ cú pháp riêng |
| Chưa tạo `routers/` | Mới có một endpoint; tách router khi có endpoint nghiệp vụ |

## Cách chạy và tự test

```powershell
cd D:\ProjectPython\english-companion
.venv\Scripts\activate
pytest -v                          # chạy test
uvicorn app.main:app --reload      # mở http://127.0.0.1:8000/health và /docs
```
`/docs` là trang Swagger do FastAPI tự sinh, dùng để thử API bằng tay.

Thử làm test đỏ: đổi `"ok"` thành `"okk"` trong `app/main.py`, chạy `pytest`, đọc thông báo `AssertionError`, rồi đổi lại.

## Lỗi đã gặp

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `pytest` không được nhận diện | Chưa bật venv | `.venv\Scripts\activate` hoặc `.venv\Scripts\python.exe -m pytest` |
| `running scripts is disabled` | PowerShell chặn script bật venv | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (chạy một lần) |

## Ghi chú
`.venv` dùng Python 3.13 trong khi CLAUDE.md và Dockerfile ghi 3.12. Đã ghi vào `progress.md` để thống nhất sau.
