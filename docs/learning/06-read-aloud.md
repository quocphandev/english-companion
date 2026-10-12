# 06. Đọc hội thoại bằng giọng của trình duyệt (một phần FR09)

## Mục tiêu
- Nút **Đọc hội thoại** đọc lần lượt các tin nhắn: cả hai bên, hoặc chỉ chatbot.
- Có **Tạm dừng/Tiếp tục**, **Trước/Sau**, **Dừng**, tốc độ **0,75 / 1,0**.
- Tô nổi bật tin đang đọc và tự cuộn tới.
- Chọn giọng theo ngôn ngữ của từng câu: tiếng Anh (en-US hoặc en-GB), tiếng Việt (vi-VN).
- **Không bao giờ tự phát âm thanh.** Dừng đọc khi gửi tin, khi rời trang hoặc tải lại trang.
- Khi thiếu giọng: báo một dòng ngắn rồi vẫn đọc tiếp. Khi trình duyệt không hỗ trợ: hiện "Trình duyệt chưa hỗ trợ đọc", chat vẫn dùng bình thường.
- Ngoại lệ đã được duyệt: đây là một phần FR09 làm sớm, **chỉ chạy trong trình duyệt**, không có backend, không thêm thư viện.

## Các file
| File | Vai trò |
|---|---|
| `static/js/speech/text.js` | Hàm thuần `splitIntoChunks` (tách câu), `detectLanguage` (đoán vi/en) |
| `static/js/speech/voices.js` | Hàm thuần `pickVoice` |
| `static/js/speech/reading-queue.js` | `ReadingQueue`: con trỏ (tin, câu), bộ lọc, `advance`, `nextMessage`, `previousMessage`, `append` |
| `static/js/conversation-reader.js` | Nối hàng đợi với DOM và `speechSynthesis`; quản lý trạng thái idle / reading / paused |
| `templates/chat.html`, `static/css/chat.css` | Thanh điều khiển nằm trên vùng tin nhắn |
| `tests/js/*.test.mjs` | Test JS chạy bằng `node --test` (Node 22, không npm) |

## Khái niệm

### `speechSynthesis` và `SpeechSynthesisUtterance`
`speechSynthesis` là bộ đọc có sẵn của trình duyệt. Nó dùng giọng của hệ điều hành, không gọi dịch vụ ngoài, không tốn phí. Mỗi `SpeechSynthesisUtterance` là "một đoạn cần đọc", kèm `lang`, `voice`, `rate`, và các sự kiện `onend` / `onerror`.
```js
const u = new SpeechSynthesisUtterance("Hello there.");
u.lang = "en-US";
u.voice = pickVoice(speechSynthesis.getVoices(), "en");
u.rate = 0.75;
u.onend = () => speakNextSentence();
speechSynthesis.speak(u);
```

### Vì sao phải tách câu
1. Chrome có thể **tự dừng giữa chừng** khi một đoạn đọc quá dài, mà không báo lỗi.
2. `rate`, `lang` và `voice` gắn với cả đoạn. Tách câu thì câu Việt dùng giọng Việt, câu Anh dùng giọng Anh, và đổi tốc độ có hiệu lực từ câu sau.
3. `pause()` và `resume()` trên Chrome hay bị kẹt. Vì vậy dự án **tự làm tạm dừng**: gọi `cancel()` và nhớ vị trí; khi tiếp tục thì đọc lại từ đầu câu đó.

### Tách logic thuần khỏi DOM để test được
Phần "tách câu, đoán ngôn ngữ, chọn giọng, di chuyển con trỏ" không đụng tới `document` hay `speechSynthesis`, nên chạy được bằng `node --test`. File `conversation-reader.js` chỉ làm nhiệm vụ nối các phần đó với giao diện.

### Số "phiên đọc" để bỏ qua callback cũ
Sau khi gọi `cancel()`, trình duyệt vẫn có thể chạy `onend` của câu vừa bị dừng, làm hàng đợi tự đọc tiếp. Mỗi lần bắt đầu, tạm dừng hoặc nhảy, biến `session` tăng thêm 1; callback nào mang số phiên cũ thì bị bỏ qua.

### Cache trình duyệt và `Cache-Control: no-cache`
Khi kiểm tra, trình duyệt vẫn chạy **file JS cũ** dù server đã có bản mới. Lý do: file tĩnh không có header `Cache-Control`, nên trình duyệt tự đoán được giữ cache một thời gian. Giờ app gửi `Cache-Control: no-cache`: trình duyệt vẫn cache, nhưng mỗi lần đều hỏi lại server; file không đổi thì server chỉ trả về mã 304 rất nhẹ.

## Luồng trạng thái
```
idle ──[Đọc hội thoại]──► reading ──[Tạm dừng]──► paused ──[Tiếp tục]──► reading
  ▲                         │  [Trước/Sau]: nhảy và đọc ngay      │ [Trước/Sau]: chỉ đổi tin được tô, không phát tiếng
  └──[Dừng / đọc xong / gửi tin]───────────────────────────────────┘
```

## Quyết định và lý do
| Quyết định | Lý do |
|---|---|
| Tự làm tạm dừng bằng `cancel()` | `pause()` của Chrome không ổn định |
| Đổi tốc độ có hiệu lực từ câu kế tiếp | Câu ngắn nên chờ ít; không phải ngắt câu đang đọc |
| Chỉ đọc tin nhắn, không đọc thẻ sửa | Spec có nút Nghe riêng cho câu sửa (giai đoạn 2) |
| Báo thiếu giọng **một lần cho mỗi ngôn ngữ** | Không làm phiền người dùng, vẫn đọc bằng giọng mặc định |

## Cách tự test
```powershell
node --test "tests/js/**/*.test.mjs"
```
Trên giao diện, mở một hội thoại có vài lượt:
1. Bấm Đọc: nghe đọc lần lượt, khung xanh chạy theo tin đang đọc.
2. Bấm Tạm dừng, rồi bấm Sau: chỉ đổi tin được tô. Bấm Tiếp tục: đọc tin đó.
3. Chọn tốc độ 0,75: câu tiếp theo đọc chậm hơn.
4. Đang đọc thì gửi một tin mới: đọc dừng lại.
5. Edge thường có giọng Việt; Chrome trên Windows có thể không có, khi đó sẽ thấy dòng thông báo thiếu giọng.

## Lỗi đã gặp
| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| Nút "■ Dừng" luôn hiện | CSS `.button { display }` thắng thuộc tính `hidden` | Thêm quy tắc chung `[hidden] { display: none !important; }` |
| Trình duyệt chạy JS cũ sau khi sửa | Thiếu `Cache-Control` | `RevalidatedStaticFiles` gửi `no-cache` |
| `node --test tests/js/` báo lỗi | Node 22 cần glob | `node --test "tests/js/**/*.test.mjs"` |
