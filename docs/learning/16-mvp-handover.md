# 16. Bàn giao MVP: README, khóa phiên bản, dữ liệu demo, nghiệm thu (Mốc 4)

## Mục tiêu
Mốc 4 trong SPEC (mục 10) yêu cầu: "Chạy trọn một buổi học và nghiệm thu AC01 đến AC08". Phần bàn giao gồm 4 việc:
- người khác cài được app theo README;
- cài lại ra đúng phiên bản thư viện đã thử;
- có dữ liệu mẫu để xem nhanh;
- có bảng ghi rõ AC nào đạt và bằng chứng nào (nằm trong `progress.md`).

## File đã tạo/sửa
| File | Vai trò |
|---|---|
| `README.md` | Cài đặt cho Windows và macOS, chọn AI, lệnh hằng ngày, lỗi hay gặp |
| `requirements.lock.txt` | Ghim đúng phiên bản mọi thư viện (cả thư viện phụ) |
| `scripts/seed_demo.py` | Thêm một hội thoại demo, một lỗi đã sửa, 2 từ đã lưu, không gọi AI |
| `tests/integration/test_seed_demo.py` | Script chỉ thêm một lần; dữ liệu hiện được trên trang |
| `progress.md`, `CLAUDE.md` | Bảng nghiệm thu; dòng "Giai đoạn hiện tại" chuyển sang MVP đã xong |

## Khái niệm mới

### File khóa phiên bản (lock file)
`requirements.txt` chỉ ghi `fastapi`, nên mỗi lần cài sẽ lấy bản mới nhất lúc đó. Hôm nay app chạy được, nhưng vài tháng sau cài lại có thể ra bản khác và hỏng. `pip freeze` in ra **mọi** gói đang có trong `.venv`, kèm số phiên bản chính xác:
```
fastapi==0.143.0
starlette==...   # thư viện phụ cũng được ghim
```
Cài bằng `pip install -r requirements.lock.txt` thì ra đúng bộ đã chạy test. Khi muốn nâng cấp: sửa `requirements*.txt`, cài lại, chạy test, rồi `pip freeze` lại.

### Seed script idempotent
"Seed" là đổ dữ liệu mẫu vào DB. "Idempotent" nghĩa là chạy một lần hay nhiều lần đều cho cùng kết quả. Script kiểm tra trước xem đã có hội thoại tên `Demo: a weekend trip` chưa; có rồi thì không làm gì:
```python
if session.scalar(select(Conversation.id).where(Conversation.topic == DEMO_TOPIC)):
    return None
```

## Luồng chạy của `seed_demo`
1. Lấy profile mặc định (chưa có thì tạo).
2. Tạo hội thoại A2, chế độ học.
3. Thêm câu mở đầu của chatbot, rồi 2 lượt chat. Lượt đầu có lỗi `I go → I went`.
4. Lưu từ `book` và `look after`:
   - Dùng chung hàm `normalize_lemma` và `meaning_key` với API, nên không tạo trùng với từ bạn đã lưu trước đó.
   - Mỗi từ có liên kết nguồn tới câu của chatbot và một lần ôn "Chưa nhớ".
5. Commit một lần. Lỗi giữa chừng thì không ghi gì.

## Quyết định và lý do
- **Seed ghi thẳng bằng ORM, không đi qua API với AI giả.** Script không cần bật server và không ghi `ai_runs`. Đổi lại, nếu sau này schema đổi thì phải sửa script; test `test_seed_demo.py` sẽ báo khi điều đó xảy ra.
- **Seed không bao giờ xóa dữ liệu.** Script chạy trên DB thật (`DATABASE_URL`). Theo quy tắc dự án, việc xóa dữ liệu phải hỏi trước.
- **Dockerfile vẫn cài từ `requirements.txt`.** File lock được tạo trên Python 3.13, còn Docker dùng 3.12. Hai phiên bản cần thống nhất trước (đã ghi trong "Ý tưởng sau"), rồi mới cho Docker dùng file lock.
- **Bảng nghiệm thu tách "đường ống" và "chất lượng".** Test tự động không gọi AI thật, nên chỉ chứng minh được luồng dữ liệu. Câu sửa của Gemini có đúng nghĩa hay không thì phải có người chấm qua `scripts.run_eval`.

## Cách chạy và tự test
```bash
python -m scripts.seed_demo      # "Demo conversation created: /conversations/N"
python -m scripts.seed_demo      # lần 2: "Demo data already exists; nothing added."
pytest tests/integration/test_seed_demo.py -q
```
Mở `/conversations/N` để xem thẻ sửa lỗi. Trang Từ vựng sẽ có `book` và `look after`, còn trang Ôn tập có 2 thẻ.

## Lỗi đã gặp
- Ruff báo `ISC004` vì một chuỗi dài bị tách hai dòng ngay trong list. Python tự nối hai chuỗi đứng cạnh nhau, nên ruff nghi là thiếu dấu phẩy. Đã sửa bằng cách bọc chuỗi trong `( ... )`.
- Test đầu tiên dùng `json()["words"]`, nhưng `GET /api/vocabulary` trả về list trực tiếp. Đã sửa lại test cho khớp với API.
