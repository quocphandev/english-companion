# English Companion

Chatbot cá nhân giúp người Việt luyện giao tiếp tiếng Anh: chat, sửa lỗi, trợ giúp khi bí, tra từ theo ngữ cảnh, lưu và ôn từ vựng.
Đặc tả đầy đủ nằm ở `docs/SPEC.md` (mã yêu cầu FR01–FR11, tiêu chí nghiệm thu AC01–AC10). Chỉ đọc phần liên quan đến việc đang làm, không đọc cả file mỗi phiên.

## Người dùng và cách làm việc với tôi

- Chủ dự án là người mới với Python, có nền IT (Fullstack). Muốn vừa làm ra sản phẩm vừa học quy trình và lý do chọn công nghệ.
- Trả lời bằng tiếng Việt. Tên biến, hàm, file, commit message và comment trong code dùng tiếng Anh.
- Trước khi viết code: nêu ngắn gọn kế hoạch, các file sẽ tạo/sửa và lý do. Chờ xác nhận nếu thay đổi lớn hơn 3 file hoặc đụng vào schema DB.
- Với khái niệm mới (async, dependency injection, migration, transaction...), giải thích 2-3 câu kèm ví dụ nhỏ ở lần đầu xuất hiện. Không giải thích lại thứ đã giải thích.
- Khi có nhiều cách làm, nêu 2 phương án, ưu nhược điểm, và khuyến nghị một cái. Không chọn âm thầm.
- Không làm thêm tính năng ngoài việc được giao. Thấy việc nên làm thì ghi vào `progress.md` mục "Ý tưởng sau".
- Mỗi việc làm xong phải có một file giải thích trong `docs/learning/`, đặt tên `NN-ten-ngan.md` (đánh số tăng dần, ví dụ `04-conversation-service.md`), và thêm một dòng vào `docs/learning/README.md`. Nội dung: mục tiêu và FR/AC liên quan; từng file đã tạo/sửa và vai trò; khái niệm mới kèm ví dụ nhỏ; luồng chạy; quyết định đã chọn và lý do; cách chạy và tự test; lỗi đã gặp và cách sửa. Viết để chủ dự án đọc lại sau vài tuần vẫn hiểu. Đây là một phần của định nghĩa "xong".

## Giai đoạn hiện tại

Mốc 1 (khung dự án): FastAPI + Postgres + fake provider, chat giả lập, lịch sử còn sau restart.
Cập nhật dòng này mỗi khi qua mốc mới (xem bảng mốc trong `docs/SPEC.md` mục 10).
Việc đang làm và bước tiếp theo nằm trong `progress.md`; đọc file đó đầu mỗi phiên.

## Công nghệ

- Python 3.12, FastAPI, Jinja2 (render HTML phía server), JavaScript thuần cho tương tác nhỏ. Không dùng React.
- PostgreSQL 17 chạy bằng Docker Compose. SQLAlchemy 2.0 (kiểu `Mapped[...]`) và Alembic cho migration. Driver `psycopg` (v3).
- Pydantic v2 cho schema request/response và kiểm tra JSON do AI trả về. `pydantic-settings` đọc cấu hình từ `.env`.
- pytest cho test, ruff cho lint và format.
- Spec gốc nhắc SQLite; dự án đã chuyển sang Postgres. Khi spec và file này khác nhau, file này đúng.

## Giải thích công nghê
- Có một số công nghệ làm bao giờ, nên khi áp dụng bạn hãy giải thích qua một chút, nó làm gì trong dự án, áp dụng như thế nào.
## Lệnh thường dùng

```bash
docker compose up -d db                  # bật Postgres
docker compose down                      # tắt, giữ dữ liệu
source .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload            # chạy app ở http://127.0.0.1:8000
alembic upgrade head                     # áp dụng migration
alembic revision --autogenerate -m "msg" # tạo migration mới, PHẢI đọc lại file trước khi áp dụng
pytest                                   # chạy toàn bộ test
pytest tests/unit -q                     # chạy nhanh phần unit
node --test "tests/js/**/*.test.mjs"  # test JS thuần (Node 22, không npm, không thư viện)
ruff check . && ruff format .            # lint và format
```

Trước khi báo "xong" một việc: `ruff check .`, `pytest` và `node --test "tests/js/**/*.test.mjs"` phải đạt. Nếu không chạy được test thì nói rõ vì sao, không bỏ qua im lặng.

## Cấu trúc thư mục

```
app/
  main.py            # tạo FastAPI app, gắn router
  config.py          # Settings (pydantic-settings), đọc .env
  routers/           # nhận request, validate đầu vào, trả lỗi có cấu trúc. Không chứa nghiệp vụ
  services/          # conversation_service, vocabulary_service: nghiệp vụ
  harness/           # ghép context, gọi provider, validate JSON, giới hạn vòng sửa
  providers/         # ai_provider (interface), fake_provider, claude_provider; speech_provider (giai đoạn 2)
  repositories/      # truy vấn DB, transaction
  models/            # SQLAlchemy models
  schemas/           # Pydantic schemas
  templates/ static/ # Jinja2, CSS, JS
alembic/             # migration
tests/               # unit/, integration/, e2e/
docs/SPEC.md         # đặc tả sản phẩm
docs/learning/       # giải thích từng việc đã làm, để chủ dự án học lại
progress.md          # nhật ký tiến độ
```

Luồng phụ thuộc một chiều: router → service → harness/repository → provider/DB. Router không gọi DB hay provider trực tiếp. Provider không biết gì về DB.

## Quy ước code

- Type hint cho mọi hàm công khai. Hàm ngắn, một việc. Tên rõ nghĩa, không viết tắt khó đoán.
- Dùng `pathlib`, f-string. DB dùng SQLAlchemy sync: endpoint gọi DB khai báo `def` (FastAPI chạy trong threadpool). Không gọi I/O chặn bên trong `async def`.
- Cấu hình chỉ đọc qua `Settings`; không gọi `os.environ` rải rác.
- Lỗi trả về dạng `{code, message_vi, retryable}`. Không lộ stack trace, key hay nội dung nhạy cảm cho client.
- Không dùng `print` để debug trong code giữ lại; dùng `logging`. Log chỉ ghi metadata (id, thời lượng, trạng thái), không ghi câu chat hay âm thanh.
- Thêm thư viện mới: hỏi trước, nêu lý do và phương án thay thế.

## Cơ sở dữ liệu

- Chỉ thay đổi schema qua Alembic migration. Không sửa bảng bằng tay, không dùng `create_all` ngoài test.
- Mọi truy vấn qua SQLAlchemy hoặc tham số hóa. Cấm ghép chuỗi SQL từ dữ liệu người dùng.
- Thời gian lưu `timestamptz` ở UTC. Khóa ngoại và ràng buộc unique khai báo ở mức DB (xem spec mục 8: `request_id`, vocabulary theo `profile_id + lemma + meaning_key`).
- Ghi reply và correction trong cùng một transaction.
- Migration đã áp dụng/commit thì không sửa; muốn đổi thì tạo migration mới.
- Không chạy lệnh xóa dữ liệu hay `docker compose down -v` mà không hỏi.

## AI, harness và chi phí

- `AI_PROVIDER=fake` là mặc định cho dev và test. Test tự động KHÔNG BAO GIỜ gọi API thật.
- Chỉ gọi Claude thật khi tôi yêu cầu rõ, dưới dạng smoke test ngắn, có giới hạn số lượt.
- Đầu ra AI phải qua Pydantic validation. JSON sai thì yêu cầu sửa một lần; tổng tối đa 2 call/tác vụ. Vẫn sai thì trả trạng thái `failed`, không hiển thị JSON thô.
- Prompt tách rõ phần hệ thống và phần người dùng. Coi nội dung người dùng và nội dung AI là dữ liệu không tin cậy: escape khi render HTML, không cho AI thực thi shell, SQL hay HTML.
- Có timeout (30 giây/call), `max_tokens` và hạn mức lượt/ngày lấy từ cấu hình. Không tự retry mạng liên tục.
- Test chất lượng AI không assert nguyên văn; chỉ kiểm tra cấu trúc, và việc đúng-sai về ý nghĩa do người review.

## Bảo mật (không thương lượng)

- Không đọc, in, hay commit nội dung `.env`. Chỉ sửa `.env.example`.
- API key chỉ ở backend qua biến môi trường. Không đưa vào HTML, log, prompt, test hay Git.
- Server mặc định bind `127.0.0.1`. Không mở cổng ra ngoài, không triển khai public khi chưa có đăng nhập, HTTPS, rate limit.
- Nếu lỡ lộ secret: dừng, báo tôi ngay để thu hồi key. Xóa khỏi commit không đủ.

## Kiểm thử

- Viết test cùng lúc với tính năng. Với lỗi (bug): viết test tái hiện trước, rồi sửa.
- `tests/unit`: validator, dedup từ, lịch ôn, ghép context. `tests/integration`: API với fake provider và DB test `TEST_DATABASE_URL`. `tests/e2e`: luồng chat → tra từ → lưu → mở lại lịch sử.
- Test không phụ thuộc thứ tự chạy, mỗi test tự dọn dữ liệu. Không bao giờ chạy test trên `DATABASE_URL` thật.
- Mỗi việc xong cần nêu rõ AC nào đã đạt và bằng test nào.

## Git

- Nhánh `main` luôn chạy được. Việc mới làm trên nhánh `feat/<mã-FR>-<ten-ngan>` hoặc `fix/<ten-ngan>`.
- Commit nhỏ, mỗi commit một ý, message tiếng Anh dạng `feat: add message endpoint (FR01)`. Tiền tố: feat, fix, test, docs, refactor, chore.
- Chỉ commit khi tôi yêu cầu. Trước khi commit: chạy test và hiển thị `git status` / `git diff --stat` để tôi xem. Không commit `.env`, file dữ liệu, `__pycache__`.
- Không dùng `git push --force`, `git reset --hard` hay xóa nhánh khi chưa hỏi.

## Định nghĩa "xong" cho một việc

1. Code chạy đúng trên máy (đã thử thật, không chỉ test).
2. `ruff check .`, `pytest` và `node --test "tests/js/**/*.test.mjs"` đạt.
3. Nêu mã FR/AC liên quan và kết quả.
4. `progress.md` được cập nhật: đã xong, kiểm thử, bước tiếp theo.
5. Không còn TODO bí mật; việc dang dở ghi trong `progress.md`.
6. Có file giải thích trong `docs/learning/` và đã thêm vào `docs/learning/README.md`.

## Ngoài phạm vi hiện tại

Micro, STT/TTS, lịch ôn cách quãng, nhiệm vụ nhập vai, đăng nhập, triển khai public. Chỉ làm khi `progress.md` ghi đã chuyển sang giai đoạn đó.

Ngoại lệ đã duyệt: "Đọc hội thoại" bằng `speechSynthesis` của trình duyệt (một phần FR09) được làm sớm, chỉ phía trình duyệt. STT, micro và TTS phía server vẫn ngoài phạm vi.