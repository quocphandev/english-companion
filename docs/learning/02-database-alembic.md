# 02. Models, kết nối Postgres và Alembic migration

## Mục tiêu

Cho app lưu dữ liệu vào Postgres để lịch sử còn sau restart. Tạo 3 bảng `profiles`, `conversations`, `messages` theo SPEC mục 8, migration đầu tiên, và một integration test chạy trên DB test riêng.
Chưa có endpoint.

- Mốc 1. Nền cho FR01; nền cho AC01 (unique `request_id` chặn lượt trùng ở mức DB, đạt đủ khi có endpoint).

## Các file

| File | Vai trò |
|---|---|
| `app/db.py` | `create_db_engine(url)`, `get_engine()`, `SessionLocal`, `get_session()` |
| `app/models/base.py` | Class `Base` cho mọi model, kèm quy tắc đặt tên constraint |
| `app/models/profile.py`, `conversation.py`, `message.py` | Mỗi file một bảng |
| `app/models/__init__.py` | Import cả 3 model để Alembic thấy đủ bảng |
| `alembic.ini` | Cấu hình Alembic. **`sqlalchemy.url` để trống**: không ghi mật khẩu vào file commit |
| `alembic/env.py` | Lấy URL từ `Settings` (hoặc URL test truyền vào), trỏ `target_metadata = Base.metadata` |
| `alembic/script.py.mako` | Mẫu sinh file migration (đã chỉnh sang cú pháp mới cho ruff) |
| `alembic/versions/..._create_profiles_conversations_messages.py` | Migration đầu tiên |
| `tests/integration/conftest.py` | Fixture `db_engine`, `db_session` dùng chung |
| `tests/integration/test_models.py` | Tạo profile → conversation → message rồi đọc lại |
| Sửa: `app/config.py` | `database_url` thành bắt buộc |
| Sửa: `docker-compose.yml` | Cổng `127.0.0.1:5432:5432` (chỉ máy bạn kết nối được) |
| Sửa: `.env.example` | Host `127.0.0.1` thay cho `localhost` |
| Sửa: `pyproject.toml` | Báo ruff rằng `alembic` là thư viện ngoài |

## Khái niệm

### Model
Class Python mô tả một bảng; mỗi thuộc tính là một cột.
```python
class Message(Base):
    __tablename__ = "messages"
    original_text: Mapped[str] = mapped_column(Text)  # TEXT NOT NULL
    request_id: Mapped[str | None] = mapped_column(unique=True)  # được NULL
```
`Mapped[str]` là bắt buộc (NOT NULL), `Mapped[str | None]` là cho phép NULL.

### Engine, Session, Transaction
- **Engine**: giữ cấu hình và "hồ" kết nối (connection pool) tới Postgres. Cả app dùng một engine.
- **Session**: phiên làm việc, giống giỏ hàng.
  ```python
  session.add(msg)  # bỏ vào giỏ
  session.flush()  # gửi SQL xuống DB, chưa chốt
  session.commit()  # chốt vĩnh viễn
  session.rollback()  # hủy những gì chưa chốt
  ```
- **Transaction**: nhóm thay đổi "tất cả thành công hoặc không gì cả". Vì vậy reply và correction phải ghi cùng một transaction.

### Relationship
```python
conversation.messages  # list Message, sắp theo created_at
message.conversation  # đi ngược lại
```
SQLAlchemy tự viết câu JOIN/SELECT khi bạn truy cập các thuộc tính này.

### Migration (Alembic)
File Python mô tả một bước đổi schema, có `upgrade()` và `downgrade()`. Alembic lưu phiên bản hiện tại của DB trong bảng `alembic_version`.
```powershell
alembic revision --autogenerate -m "msg"   # so models với DB, soạn nháp migration
alembic upgrade head                       # chạy các bước còn thiếu
alembic downgrade -1                       # lùi một bước
alembic current                            # DB đang ở phiên bản nào
```
**Luôn đọc lại file autogenerate** trước khi `upgrade`: công cụ có thể bỏ sót hoặc sinh sai.
Migration đã áp dụng/commit thì không sửa; muốn đổi thì tạo migration mới.

### Fixture (pytest)
Hàm chuẩn bị tài nguyên cho test. Test chỉ cần ghi tên fixture làm tham số là được cấp.
```python
def test_create_conversation_with_message(db_session: Session) -> None: ...
```
`scope="session"`: chạy một lần cho cả lượt pytest. Mặc định: mỗi test một lần.

### Savepoint và rollback trong test
`db_session` mở một transaction ngoài; bên trong, `commit()` của test chỉ chốt một **savepoint** (điểm lưu tạm). Hết test thì rollback transaction ngoài, nên dữ liệu biến mất. Mỗi test tự dọn, không phụ thuộc thứ tự chạy.

## Thiết kế bảng

| Bảng | Điểm chính |
|---|---|
| `profiles` | `level` A1–B2 (mặc định A2), `correction_mode` learning/conversation, `timezone`, `reuse_words` |
| `conversations` | FK `profile_id` (`ON DELETE CASCADE`), `topic`, `status` active/finished, `summary`, `created_at` |
| `messages` | FK `conversation_id` (CASCADE), `role` user/assistant, `original_text`, `input_mode`, `status` pending/succeeded/failed, `request_id` UNIQUE được NULL, `created_at` |

- Thời gian: `DateTime(timezone=True)` → `timestamptz`, mặc định `now()`; engine đặt timezone UTC nên giá trị đọc ra luôn ở UTC.
- `request_id`: lượt user mang id, reply AI để NULL. Postgres cho phép nhiều NULL trong cột unique.

## Quyết định và lý do

| Quyết định | Lý do |
|---|---|
| SQLAlchemy **sync**, endpoint gọi DB dùng `def` | Dễ học; tránh lỗi psycopg async với event loop mặc định trên Windows. FastAPI chạy hàm `def` trong threadpool nên không chặn server |
| `VARCHAR` + `CHECK` thay vì kiểu `ENUM` của Postgres | Thêm giá trị vào ENUM cần migration phức tạp; CHECK chỉ cần đổi điều kiện |
| Naming convention trong `Base` | Constraint có tên ổn định (`uq_messages_request_id`), migration sau sinh đúng tên |
| Test dựng schema bằng `alembic upgrade head` thay vì `create_all` | Kiểm tra luôn cả file migration |
| Test fail ngay nếu `TEST_DATABASE_URL` trống hoặc trùng `DATABASE_URL` | Không bao giờ chạy test trên dữ liệu thật |
| `ON DELETE CASCADE` | Spec yêu cầu xóa hội thoại thì xóa luôn tin nhắn |

## Cách chạy và tự test

```powershell
docker compose up -d db
.venv\Scripts\activate
alembic current                    # phải hiện 33b5d3751464 (head)
pytest tests/integration -v
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d messages"'
```
(`sh -c` để lấy user và tên DB từ biến môi trường trong container, khỏi gõ tay.)
Lệnh cuối cho xem cấu trúc bảng thật: kiểu `timestamp with time zone`, unique, FK, CHECK.

## Lỗi đã gặp

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| `alembic` treo không phản hồi | Sau khi đổi cổng thành `127.0.0.1`, `localhost` trên Windows thử IPv6 `::1` trước, không có gì ở đó nên treo | Dùng `127.0.0.1` trong `DATABASE_URL`/`TEST_DATABASE_URL`; thêm `connect_timeout=10` để lỗi nhanh thay vì treo |
| ruff báo lỗi file migration | Template Alembic dùng cú pháp cũ (`Union`), và ruff tưởng `alembic` là code của dự án do có thư mục `alembic/` | Sửa `script.py.mako`, thêm `known-third-party = ["alembic"]` |
| Postgres mở cho cả mạng LAN | `ports: "5432:5432"` | Đổi thành `127.0.0.1:5432:5432` |
