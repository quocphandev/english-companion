# English Companion

Chatbot cá nhân giúp người Việt luyện nói tiếng Anh. Các tính năng chính:
- chat, sửa lỗi theo hai chế độ;
- trợ giúp khi bí;
- bấm vào từ để tra nghĩa theo ngữ cảnh;
- lưu từ và ôn bằng flashcard;
- tổng kết khi kết thúc buổi;
- đọc hội thoại bằng giọng của trình duyệt.

Đặc tả đầy đủ ở `docs/SPEC.md`. Tiến độ và bảng nghiệm thu ở `progress.md`. Các bài giải thích từng phần ở `docs/learning/`.

> Chỉ chạy trên máy cá nhân: server bind `127.0.0.1`, chưa có đăng nhập. Đừng mở ra Internet.

## Cần có
- Python 3.12 trở lên. Bản đã thử là 3.13.
- Docker Desktop (để chạy PostgreSQL 17).
- Node 22, chỉ cần nếu muốn chạy test JS.

## Cài đặt lần đầu

**Windows (PowerShell)**
```powershell
git clone https://github.com/quocphandev/english-companion.git
cd english-companion
copy .env.example .env            # rồi sửa mật khẩu DB trong .env nếu muốn
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.lock.txt
docker compose up -d db
docker compose exec db createdb -U english english_companion_test   # DB riêng cho test
alembic upgrade head
python -m scripts.seed_demo       # (tùy chọn) thêm một hội thoại và 2 từ mẫu
uvicorn app.main:app --reload
```

**macOS / Linux**
```bash
git clone https://github.com/quocphandev/english-companion.git
cd english-companion
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
docker compose up -d db
docker compose exec db createdb -U english english_companion_test
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000.

- Nếu bạn đổi `POSTGRES_USER` trong `.env`, hãy thay `english` trong lệnh `createdb` bằng tên mới.
- `requirements.lock.txt` ghim đúng phiên bản đã thử. `requirements.txt` và `requirements-dev.txt` chỉ liệt kê tên thư viện.

## Chọn AI
- `AI_PROVIDER=fake` là mặc định: không gọi dịch vụ ngoài, không tốn tiền, phù hợp để thử giao diện.
- Muốn dùng Gemini thật:
  1. Lấy key ở https://aistudio.google.com/apikey.
  2. Điền vào `.env`: `AI_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `GEMINI_MODEL=...`.
  3. Khởi động lại server.
- Key chỉ nằm trong `.env` (đã có trong `.gitignore`). Đừng commit hay dán key vào bất cứ đâu.
- `DAILY_AI_LIMIT` giới hạn số lần gọi AI mỗi ngày. Trang **Cài đặt** cho biết hôm nay đã dùng bao nhiêu lượt.

## Lệnh hằng ngày
```bash
docker compose up -d db        # bật DB
docker compose down            # tắt DB, giữ dữ liệu
uvicorn app.main:app --reload  # chạy app
pytest                         # test (dùng TEST_DATABASE_URL, không đụng dữ liệu thật)
node --test "tests/js/**/*.test.mjs"
ruff check . && ruff format .
```

Muốn chấm chất lượng sửa lỗi với Gemini thật (khoảng 30–60 lượt gọi):
- PowerShell: `$env:RUN_LIVE_AI="1"; python -m scripts.run_eval`
- macOS: `RUN_LIVE_AI=1 python -m scripts.run_eval`

Kết quả ghi vào `eval_results/` để người chấm.

## Deploy bản demo public (Render + Neon, miễn phí)

Bản demo dùng **chung một bộ dữ liệu**. Ai có mật khẩu cũng thấy hội thoại và từ vựng của nhau, nên chức năng xóa bị tắt. Đừng dùng bản demo để học thật.

1. **Tạo database ở Neon** (https://neon.tech):
   - Đăng ký và tạo project. Nên chọn region gần Singapore.
   - Copy *connection string*, dạng `postgresql://user:pass@ep-....neon.tech/neondb?sslmode=require`. Để nguyên dạng này; app tự đổi sang driver psycopg.
2. **Tạo key Gemini mới** chỉ dùng cho bản demo, để có thể thu hồi riêng.
3. **Tạo service ở Render** (https://render.com):
   - Đăng ký bằng GitHub.
   - Vào **New → Blueprint**, chọn repo này. Render đọc `render.yaml` và hỏi 3 giá trị bí mật:
     - `DATABASE_URL`: connection string của Neon;
     - `GEMINI_API_KEY`: key mới ở bước 2;
     - `APP_PASSWORD`: mật khẩu dài, ngẫu nhiên.
   - Các biến khác đã khai báo sẵn trong `render.yaml`:
     - `AI_PROVIDER=gemini`
     - `PUBLIC_DEMO=true`
     - `RATE_LIMIT_PER_MINUTE=10`
     - `DAILY_AI_LIMIT=50`
4. **Đợi build xong** (vài phút):
   - Mỗi lần khởi động, container tự chạy `alembic upgrade head` rồi mới bật app.
   - Mở link `https://english-companion-xxxx.onrender.com`. Trình duyệt hiện hộp đăng nhập: tên gõ gì cũng được, mật khẩu là `APP_PASSWORD`.
5. **Gửi link và mật khẩu cho người thử**, qua hai kênh riêng nếu được.

Lưu ý:
- **Bản free của Render ngủ** sau khoảng 15 phút không ai dùng. Lần vào đầu tiên sau đó mất khoảng 30–60 giây để khởi động.
- Mỗi lần push lên `master`, Render tự build lại.
- **Tắt bản demo:** vào Render chọn *Suspend* service, rồi thu hồi key Gemini ở AI Studio.
- **Thử image trên máy:** `docker build -t english-companion .`

## Gặp lỗi
- **`alembic` hoặc app treo khi kết nối DB:** dùng `127.0.0.1`, không dùng `localhost`, trong `DATABASE_URL`.
- **Test báo `TEST_DATABASE_URL is not set`:** điền biến này trong `.env` và tạo DB test bằng lệnh `createdb` ở trên.
- **Tiếng Việt bị lỗi khi chạy script trên Windows:** đặt `$env:PYTHONIOENCODING="utf-8"`.
