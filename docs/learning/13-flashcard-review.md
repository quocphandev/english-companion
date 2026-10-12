# 13. Ôn tập bằng flashcard thủ công (FR07, bản MVP)

## Mục tiêu
- Trang **Ôn tập** hiện từng thẻ một.
  - **Mặt trước:** từ kèm câu khuyết, ví dụ "She ____ her sister."
  - **Mặt sau:** nghĩa và ví dụ.
- Hai nút **Nhớ / Chưa nhớ**. Mỗi lần trả lời được lưu vào bảng `review_events`.
- Thứ tự thẻ: từ **chưa ôn** trước, rồi từ lần trước **chưa nhớ**, cuối cùng là từ đã nhớ. Trong mỗi nhóm, từ ôn lâu nhất đứng trước.
- Trang Từ vựng có bộ lọc **Tất cả / Chưa ôn / Đã ôn**.
- FR07, phần MVP. Lịch ôn cách quãng (ôn lại sau 1, 3, 7, 14, 30 ngày) và việc đưa từ đã lưu vào hội thoại thuộc **giai đoạn 3**, chưa làm. Cột `vocabulary.due_at` đã có sẵn cho lúc đó.

## Các file
| File | Vai trò |
|---|---|
| `app/models/review_event.py` + migration `9c34ce25e825` | Bảng `review_events` (`outcome` ∈ remembered/again) |
| `app/repositories/review_repository.py` | Ghi kết quả; truy vấn bộ thẻ có sắp thứ tự |
| `app/services/review_service.py` | `make_cloze`, `cloze_from_example`, `flashcard_cloze`; `record`, `deck` |
| `app/schemas/review.py` | `ReviewIn`, `ReviewOut`, `Flashcard` |
| `app/routers/reviews.py` | `GET /api/reviews/deck`, `POST /api/reviews` |
| `app/templates/review.html`, `static/js/vocab/review-page.js` | Trang ôn tập |
| `vocabulary_repository.py`, `vocabulary.html` | Bộ lọc chưa ôn / đã ôn |

## Khái niệm

### Lấy lần ôn mới nhất của mỗi từ bằng hàm cửa sổ (window function)
```python
func.row_number().over(
    partition_by=ReviewEvent.vocabulary_id,
    order_by=(ReviewEvent.reviewed_at.desc(), ReviewEvent.id.desc()),
)
```
`row_number() OVER (PARTITION BY …)` đánh số 1, 2, 3… cho các lần ôn **của từng từ**, mới nhất mang số 1. Lấy các dòng có số 1 là được kết quả gần nhất của mỗi từ. Toàn bộ chỉ mất **một truy vấn**, không phải truy vấn riêng cho từng từ.

### Sắp xếp theo nhóm bằng `CASE`
```python
case((latest.c.outcome.is_(None), 0), (latest.c.outcome == "again", 1), else_=2)
```
Câu lệnh trên đổi trạng thái thành số 0, 1, 2 rồi sắp xếp theo số đó: chưa ôn, chưa nhớ, rồi đã nhớ.

### `EXISTS` cho bộ lọc "đã ôn"
```python
reviewed = exists().where(ReviewEvent.vocabulary_id == Vocabulary.id)
statement.where(reviewed)  # đã ôn
statement.where(~reviewed)  # chưa ôn
```

### Câu khuyết
Ưu tiên câu thật mà người học đã gặp từ đó (câu nguồn). Vì câu nguồn lưu sẵn vị trí của từ, việc che từ luôn chính xác. Nếu câu nguồn đã bị xóa cùng hội thoại, chương trình che từ đó trong câu ví dụ, chỉ khớp **nguyên từ**: "book" không bị che bên trong "bookshops".

## Quyết định và lý do
| Quyết định | Lý do |
|---|---|
| Thẻ được render sẵn ở server; JS chỉ ẩn, hiện và gửi kết quả | Ít JS, chữ được Jinja escape |
| Ghi mỗi lần trả lời thành một dòng sự kiện, không chỉ lưu trạng thái cuối | Có lịch sử đầy đủ để giai đoạn 3 tính lịch ôn |
| Lưu lỗi thì giữ thẻ để trả lời lại | Không mất kết quả |
| Mỗi lượt ôn tối đa 20 thẻ | Lượt ngắn, dễ duy trì |

## Cách tự test
```powershell
pytest tests/unit/test_review_cloze.py tests/integration/test_review_api.py -v
```
Lưu vài từ, mở "Ôn tập" ở thanh bên, bấm "Hiện nghĩa", rồi "Nhớ" hoặc "Chưa nhớ". Mở lại "Ôn tập": từ chưa nhớ được xếp lên trước từ đã nhớ.
