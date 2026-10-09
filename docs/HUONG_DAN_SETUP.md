# Hướng dẫn thiết lập: Git, Docker, Postgres, CLAUDE.md

Làm lần lượt từ trên xuống. Mỗi bước có phần "Tại sao" để bạn hiểu chứ không chỉ chép lệnh.
Lệnh chạy trong Terminal (macOS) hoặc PowerShell / Git Bash (Windows).

## Bước 0. Cài công cụ

| Công cụ | Kiểm tra | Ghi chú |
|---|---|---|
| Git | `git --version` | Windows: cài Git for Windows. macOS: `xcode-select --install` hoặc `brew install git` |
| Python 3.12 | `python --version` (hoặc `python3 --version`) | Tải từ python.org. Windows nhớ tick "Add to PATH" |
| Docker Desktop | `docker --version` và `docker compose version` | Windows cần bật WSL2 khi cài. Mở app Docker Desktop và đợi trạng thái "running" |
| Tài khoản GitHub | | Miễn phí, dùng để lưu mã nguồn trên mạng |

## Bước 1. Git: tạo kho mã nguồn

**Tại sao dùng Git:** nó lưu lịch sử mọi thay đổi, cho phép quay lại bản chạy được khi Claude hoặc bạn làm hỏng gì đó, và là cách đẩy mã lên GitHub.

1. Khai báo danh tính (một lần cho cả máy):

   ```bash
   git config --global user.name "Ten Cua Ban"
   git config --global user.email "email-ban-dung-tren-github@example.com"
   git config --global init.defaultBranch main
   ```

2. Đặt thư mục dự án (đã chứa các file trong bộ khởi tạo này) rồi khởi tạo:

   ```bash
   cd english-companion
   git init
   git status
   ```

3. **Kiểm tra `.gitignore` TRƯỚC khi commit.** File này liệt kê thứ Git phải lờ đi: `.env` (chứa mật khẩu và API key), `.venv/`, `__pycache__/`. Nếu bạn lỡ commit `.env`, coi như key đã lộ.

4. Commit đầu tiên:

   ```bash
   git add .
   git status            # đọc kỹ danh sách; KHÔNG được thấy .env
   git commit -m "chore: initial project skeleton"
   git log --oneline
   ```

5. Đẩy lên GitHub:
   - Vào github.com → New repository → tên `english-companion` → chọn **Private** → **không** tick thêm README/.gitignore → Create.
   - Chạy đúng 3 lệnh GitHub hiển thị, dạng:

     ```bash
     git remote add origin https://github.com/<tai-khoan>/english-companion.git
     git branch -M main
     git push -u origin main
     ```

   - Lần đầu GitHub hỏi đăng nhập: dùng trình duyệt (Git Credential Manager trên Windows) hoặc `gh auth login` nếu đã cài GitHub CLI. GitHub không nhận mật khẩu tài khoản khi push qua HTTPS; cần token hoặc đăng nhập qua trình duyệt.

6. Quy trình làm việc hằng ngày:

   ```bash
   git switch -c feat/fr01-send-message     # nhánh cho một việc nhỏ
   # ... làm việc, chạy test ...
   git add -A && git status                 # xem trước khi commit
   git commit -m "feat: add message endpoint (FR01)"
   git push -u origin feat/fr01-send-message
   # trên GitHub: Pull Request → xem lại diff → Merge vào main
   git switch main && git pull
   ```

   Một Pull Request tự xem lại diff là thói quen tốt để học đọc code mà Claude viết.

**Nếu lỡ commit `.env`:** thu hồi ngay key/mật khẩu cũ, tạo cái mới, rồi hỏi Claude cách xóa khỏi lịch sử. Chỉ xóa file ở commit sau là không đủ.

## Bước 2. Cấu hình môi trường

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

Mở `.env`, đổi `POSTGRES_PASSWORD` và sửa cùng mật khẩu đó trong `DATABASE_URL` và `TEST_DATABASE_URL`. Giữ `AI_PROVIDER=fake` cho đến khi cần gọi Claude thật.

**Tại sao tách `.env`:** mật khẩu và key nằm ngoài mã nguồn, mỗi máy một giá trị, không bao giờ lên Git. `.env.example` là bản mẫu không chứa bí mật, được commit.

## Bước 3. Docker + Postgres

**Docker** đóng gói chương trình cùng môi trường chạy của nó, nên Postgres chạy giống nhau trên mọi máy mà bạn không phải cài trực tiếp. **Docker Compose** mô tả nhiều dịch vụ trong một file `docker-compose.yml`.

Khởi động Postgres:

```bash
docker compose up -d db
docker compose ps                 # trạng thái phải là "healthy" sau vài giây
docker compose logs db            # xem log nếu có lỗi
```

Vào thử database:

```bash
docker compose exec db psql -U english -d english_companion
```

Trong `psql`: `\l` liệt kê database (phải thấy `english_companion` và `english_companion_test`), `\dt` liệt kê bảng, `\q` để thoát.

Những điều cần hiểu trong `docker-compose.yml`:

- `volumes: pgdata` là nơi dữ liệu thật nằm. `docker compose down` giữ dữ liệu, `docker compose down -v` **xóa** dữ liệu.
- `127.0.0.1:5432:5432` chỉ cho máy bạn truy cập Postgres, không lộ ra mạng.
- `healthcheck` giúp service `app` đợi Postgres sẵn sàng.
- Thư mục `docker/initdb` chỉ chạy khi volume mới tạo. Nếu volume đã có từ trước mà thiếu DB test, chạy lệnh trong file `01-create-test-db.sql`.
- Trong container, app gọi DB bằng host `db`. Khi chạy app ngoài container, host là `localhost`. Đây là lỗi cấu hình hay gặp nhất.

**Khuyên dùng khi học:** chạy Postgres trong Docker, còn app chạy bằng `uvicorn` ngoài container (debug dễ hơn). Chạy cả app trong Docker (`docker compose --profile app up --build`) khi bạn đã quen và để chuẩn bị triển khai.

## Bước 4. Python: môi trường ảo và thư viện

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip freeze > requirements.lock.txt # ghim phiên bản đúng với yêu cầu của spec
```

**Tại sao `.venv`:** mỗi dự án có bộ thư viện riêng, không đụng nhau. Nhớ kích hoạt `.venv` mỗi lần mở terminal mới.

## Bước 5. Từ SQLite sang Postgres: những gì thay đổi so với spec

Spec ban đầu dùng SQLite. Khi chuyển, các thay đổi nên có:

1. **Dùng SQLAlchemy 2.0 + Alembic** thay cho SQL viết tay. Models mô tả bảng bằng Python; Alembic sinh file migration có phiên bản (spec mục 10 yêu cầu migration).
2. **Kiểu dữ liệu:** thời gian dùng `timestamptz`; khóa chính có thể dùng UUID hoặc số nguyên tự tăng (bàn với Claude, mặc định nên chọn số nguyên cho đơn giản); văn bản dùng `text`.
3. **Ràng buộc unique** (`request_id`, vocabulary theo `profile_id + lemma + meaning_key`) khai báo ở DB và dùng `INSERT ... ON CONFLICT` cho idempotency. Postgres làm việc này tốt hơn SQLite.
4. **Test dùng DB Postgres riêng** (`TEST_DATABASE_URL`) thay vì SQLite trong bộ nhớ, để test giống môi trường thật.
5. Cập nhật `docs/SPEC.md` mục 7, 8, 9 và 10 cho khớp (hỏi Claude: "cập nhật spec từ SQLite sang Postgres và liệt kê chỗ đã sửa").

## Bước 6. CLAUDE.md: cách viết và duy trì

`CLAUDE.md` là tờ ghi chú dự án mà Claude Code đọc ở đầu mỗi phiên. Nó không được "nhớ" từ phiên trước, nên mọi quy ước phải nằm trong file này.

**Nguyên tắc viết:**

- **Ngắn, cụ thể, kiểm chứng được.** "Chạy `pytest` trước khi báo xong" tốt hơn "hãy cẩn thận khi test".
- **Chỉ ghi những gì Claude không đoán được từ code:** lệnh chạy, quy ước riêng, quyết định kiến trúc, điều cấm.
- **Chia mục theo câu hỏi Claude sẽ có:** dự án là gì, công nghệ gì, chạy lệnh nào, code đặt ở đâu, quy ước nào, không được làm gì, thế nào là xong.
- **Quy tắc quan trọng viết bằng lời dứt khoát** ("không bao giờ", "luôn luôn") và cho một lý do ngắn.
- **Đừng dán cả spec vào đây.** Chỉ trỏ tới `docs/SPEC.md`. File dài thì quy tắc quan trọng bị loãng và tốn token mỗi phiên.
- **Cập nhật khi thực tế đổi.** Thấy Claude lặp lại một lỗi, thêm một dòng quy tắc vào file. Dòng nào không còn đúng thì xóa.

**Cách kiểm tra file có hiệu quả:** mở phiên mới và hỏi "dự án này chạy test bằng lệnh nào, và cấm làm gì với `.env`?". Nếu Claude trả lời đúng thì file hoạt động. Trong Claude Code, gõ `/memory` để xem các file đang được nạp.

**Quy trình một phiên làm việc đề xuất:**

1. Mở Claude Code trong thư mục dự án.
2. Giao một việc nhỏ kèm mã: "Làm FR01 phần tạo conversation (`POST /api/conversations`), đạt AC01. Dùng plan mode, nêu file sẽ sửa trước."
3. Duyệt kế hoạch → để Claude làm → chạy `pytest` và tự thử trên trình duyệt.
4. Xem `git diff`, hỏi về mọi đoạn bạn chưa hiểu.
5. Commit, cập nhật `progress.md`, đóng phiên.

## Danh sách kiểm tra cuối

- [ ] `git log` có commit đầu tiên, `git status` sạch, repo GitHub là Private.
- [ ] `.env` không xuất hiện trong `git status` hay trên GitHub.
- [ ] `docker compose ps` báo `db` healthy; `psql` thấy 2 database.
- [ ] `pip install -r requirements-dev.txt` thành công trong `.venv`.
- [ ] Claude Code trả lời đúng khi hỏi các quy ước trong `CLAUDE.md`.
- [ ] `progress.md` ghi đúng bước tiếp theo.

## Lỗi thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `docker: command not found` hoặc không kết nối được daemon | Docker Desktop chưa chạy | Mở Docker Desktop, đợi "running" |
| `port is already allocated` ở 5432 | Có Postgres khác đang chạy trên máy | Tắt nó hoặc đổi cổng trái thành `5433:5432` và sửa `DATABASE_URL` |
| `password authentication failed` | Đổi mật khẩu trong `.env` sau khi volume đã tạo | `docker compose down -v` (mất dữ liệu dev) rồi `up -d db` lại |
| App không kết nối DB khi chạy trong container | Dùng `localhost` thay vì `db` | Trong container host là `db` (compose đã ghi đè `DATABASE_URL`) |
| Không thấy DB `english_companion_test` | Volume có trước khi thêm script init | Chạy tay lệnh `CREATE DATABASE` ghi trong file SQL |
| `git push` bị từ chối đăng nhập | Dùng mật khẩu tài khoản qua HTTPS | Đăng nhập qua trình duyệt / `gh auth login` / token |
