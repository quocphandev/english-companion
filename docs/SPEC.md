Phiên bản 1.0 \| Ngày 09 tháng 10 năm 2026

Tài liệu mô tả sản phẩm để triển khai một chatbot cá nhân: luyện giao tiếp bằng chữ và giọng nói, nhận hỗ trợ khi bí, sửa lỗi và học từ vựng ngay trong hội thoại. Dùng làm đầu vào cho thiết kế, viết mã Python và kiểm thử nghiệm thu.

## 1 Mục tiêu sản phẩm

- Giúp người học tiếp tục hội thoại dù thiếu từ hoặc chưa biết cách diễn đạt.

- Giải thích lỗi bằng tiếng Việt, giữ ý của người học và cho phép thử lại.

- Tra nghĩa từ hoặc cụm theo ngữ cảnh, lưu và ôn trong các buổi tiếp theo.

- Tạo sản phẩm dùng được từ đầu đến cuối trước khi mở rộng nhiều tính năng.

## 2 Người dùng và quy tắc mặc định

Người dùng đầu tiên là người học tiếng Anh Việt Nam, có nền tảng IT và công việc tester. Giao diện tiếng Việt; nội dung hội thoại tiếng Anh. Mặc định câu ngắn, trình độ luyện tập A2 do người dùng tự chọn; không coi đây là kết quả đánh giá trình độ.

Tên English Companion là tên làm việc. MVP chạy local cho một người, chưa có đăng ký hoặc đăng nhập. Chủ đề đầu tiên gồm đời sống, quán cà phê và công việc tester. Các giới hạn kỹ thuật trong spec là giá trị đề xuất, có thể cấu hình.

## 3 Phạm vi theo giai đoạn

| **Giai đoạn** | **Chức năng**                                                         | **Điều kiện hoàn thành**                           |
|---------------|-----------------------------------------------------------------------|----------------------------------------------------|
| MVP           | Chat chữ, sửa lỗi, trợ giúp, tra từ và cụm, lưu từ, lịch sử, tổng kết | Luồng học hoàn chỉnh; xử lý lỗi API và lưu dữ liệu |
| Giai đoạn 2   | Micro, bản chép lời có thể sửa, nghe câu và nói lại                   | Có fallback chat chữ; kiểm thử trình duyệt         |
| Giai đoạn 3   | Ôn cách quãng, luyện lỗi cũ, nhiệm vụ và cá nhân hóa                  | Có lịch ôn và dữ liệu học thực tế                  |

Chưa làm trong các giai đoạn trên: chấm điểm phát âm chuyên sâu, chứng chỉ CEFR, mạng xã hội, thanh toán và ứng dụng mobile native. Giọng nói vẫn thuộc sản phẩm mục tiêu, được triển khai sau MVP chữ.

# 4 Hội thoại và hỗ trợ khi bí

## FR01 Bắt đầu và tiếp tục cuộc trò chuyện

Chọn chủ đề, trình độ luyện tập A1 đến B2 và cách sửa lỗi. Chatbot mở đầu bằng một câu hỏi ngắn. Người dùng gửi tiếng Anh, tiếng Việt hoặc câu trộn hai ngôn ngữ. Hệ thống giữ nguyên câu gốc, không tự thay nội dung đã gửi.

- Mỗi lượt nhận phản hồi tiếng Anh 1 đến 4 câu, thông thường có tối đa một câu hỏi tiếp nối.

- Giới hạn đầu vào đề xuất 2.000 ký tự; loại bỏ khoảng trắng để kiểm tra câu rỗng, nhưng lưu nội dung gốc.

- Trạng thái gửi rõ ràng: đang xử lý, thành công hoặc lỗi. Không tạo hai lượt khi bấm gửi nhiều lần.

- Tiếp tục lịch sử dùng đúng hội thoại đang chọn; mở cuộc trò chuyện mới không mang toàn bộ hội thoại cũ sang.

## FR02 Sửa lỗi với hai chế độ

Chế độ học hiển thị thẻ sửa ngay dưới lượt của người học: câu gốc, câu sửa, phần thay đổi và giải thích tiếng Việt. Chế độ giao tiếp tiếp tục đối thoại trước; các lỗi được xem khi người học bấm Xem lỗi hoặc kết thúc buổi.

Phân loại phản hồi: lỗi ngữ pháp, dùng từ, chính tả hoặc cách diễn đạt tự nhiên hơn. Nếu câu đúng, không tạo lỗi giả; gợi ý phong cách phải ghi rõ là tùy chọn. Mỗi lượt ưu tiên tối đa 3 điểm quan trọng. Không đánh giá phát âm chỉ từ bản chép lời.

## FR03 Cứu trợ khi bí

| **Mức**           | **Hành vi**                                                                    |
|-------------------|--------------------------------------------------------------------------------|
| 1 Gợi ý từ        | Gợi ý tối đa 3 từ hoặc cụm với nghĩa Việt.                                     |
| 2 Mở đầu câu      | Đưa khung câu để người dùng tự hoàn thành.                                     |
| 3 Câu mẫu         | Đưa một câu hoàn chỉnh phù hợp ngữ cảnh.                                       |
| Ý bằng tiếng Việt | Người dùng nhập điều muốn nói; hiển thị cách diễn đạt tiếng Anh và giải thích. |

Gợi ý không được tự gửi như lời người dùng. Có nút Chèn vào ô nhập để người học chỉnh sửa và chủ động gửi. Ghi mức trợ giúp để người học nhìn lại, không dùng làm điểm phạt.

## FR04 Thử lại sau khi được sửa

Nút Thử lại đưa người học vào bước luyện câu vừa sửa. Cho phép nói hoặc gõ cách diễn đạt khác cùng ý. So sánh theo ý nghĩa và lỗi mục tiêu, không đòi khớp nguyên văn. Kết quả ghi Nhận xét của AI; người học có thể bỏ qua và tiếp tục.

# 5 Tra nghĩa và quản lý từ vựng

## FR05 Bấm từ hoặc chọn cụm trong câu

Mỗi từ trong phản hồi tiếng Anh có thể bấm. Popup hiện nghĩa tiếng Việt trong câu, từ loại, dạng gốc nếu có, ví dụ ngắn, nghĩa cả câu tùy chọn và nút Lưu từ. Nút Nghe từ được thêm cùng phần phát giọng ở giai đoạn 2.

Trên desktop có thể bôi chọn cụm liên tiếp rồi bấm Tra cụm. Trên mobile dùng chế độ Chọn cụm với điểm bắt đầu và kết thúc. MVP cho phép tối đa 8 từ liên tiếp trong cùng một tin nhắn. Dấu câu không trở thành từ riêng; giữ được các từ có dấu nháy như don’t.

Tra cứu phải gửi cả câu chứa từ và vị trí được chọn. Không chỉ dịch một từ cô lập. Nếu chưa đủ ngữ cảnh hoặc có nhiều cách hiểu, hiển thị các khả năng và nêu điều chưa chắc chắn.

## Ví dụ nghiệm thu nghĩa theo ngữ cảnh

| **Câu gốc**                    | **Lựa chọn** | **Nghĩa mong muốn** |
|--------------------------------|--------------|---------------------|
| I read a book.                 | book         | Quyển sách          |
| I want to book a room.         | book         | Đặt phòng           |
| She looks after her sister.    | looks after  | Chăm sóc            |
| I’m testing the login feature. | feature      | Tính năng           |

## FR06 Lưu và quản lý từ

Lưu từ gồm từ hoặc cụm, dạng gốc, nghĩa trong câu, câu nguồn, ví dụ, từ loại và thời điểm lưu. Lưu lại cùng dạng gốc và cùng nghĩa cập nhật liên kết nguồn thay vì thêm bản sao. Cùng từ nhưng khác nghĩa được lưu thành mục riêng; người dùng có thể sửa nghĩa trước khi lưu.

- Danh sách từ có tìm kiếm, lọc chưa ôn hoặc đã ôn, sửa ghi chú và xóa có xác nhận.

- Popup báo Đã lưu sau thành công; lỗi lưu giữ nguyên dữ liệu popup để thử lại.

- Cache nghĩa dùng cả câu, lựa chọn, ngôn ngữ và phiên bản prompt; không tái dùng nghĩa chỉ theo mặt chữ.

## FR07 Ôn lại và gặp lại từ

MVP có flashcard thủ công: mặt trước từ kèm câu khuyết, mặt sau nghĩa và ví dụ; hai lựa chọn Nhớ và Chưa nhớ. Giai đoạn 3 đặt lịch đề xuất: chưa nhớ ôn ngày sau, nhớ ôn sau 1, 3, 7, 14 rồi 30 ngày. Lịch theo múi giờ người dùng; không tuyên bố đây là thuật toán đánh giá chính thức.

Khi cá nhân hóa, chọn tối đa 3 từ đến hạn hoặc đã lưu để đưa tự nhiên vào hội thoại. Người dùng có thể tắt chức năng này. Không ép dùng từ nếu khiến tình huống thiếu tự nhiên.

# 6 Giọng nói và trải nghiệm học

## FR08 Nói với chatbot ở giai đoạn 2

Luồng: bấm micro → cấp quyền → bắt đầu thu → dừng → chuyển âm thanh thành chữ → xem và sửa bản chép → bấm gửi. Không tự gửi bản chép lời. Có nút hủy, ghi lại và quay về gõ chữ.

- Một đoạn thu tối đa 60 giây, dung lượng tối đa đề xuất 10 MB; từ chối vượt giới hạn trước khi gửi đến dịch vụ.

- Nếu im lặng, không nhận ra tiếng hoặc bị từ chối quyền, hiển thị hướng dẫn và giữ chat chữ hoạt động.

- Người dùng chọn ngôn ngữ nói; mặc định tiếng Anh. Tiếng Việt dùng cho trợ giúp diễn đạt.

- Âm thanh không lưu lâu dài mặc định; tệp tạm được xóa sau xử lý hoặc sau 15 phút khi bị gián đoạn. Bản chép đã gửi được lưu như tin nhắn.

## FR09 Nghe và nói lại

Nút Nghe xuất hiện ở câu trả lời, câu sửa và popup từ. Cho phép dừng và chọn tốc độ 0,75 hoặc 1,0. Không tự phát âm thanh. Khi giọng hoặc tính năng trình duyệt không có sẵn, hiển thị trạng thái thay vì làm hỏng hội thoại.

Bản đầu có thể dùng speech synthesis của trình duyệt. Speech recognition trên trình duyệt có mức hỗ trợ khác nhau; tính năng thu và chuyển lời nói cần adapter có thể thay thế bằng dịch vụ STT phía Python. Chọn nhà cung cấp và kiểm tra phí trước khi tích hợp. Không giả định Claude Messages tự xử lý toàn bộ STT và TTS.

## FR10 Tổng kết cuối buổi

Kết thúc buổi tạo bản tóm tắt: nội dung đã nói, tối đa 5 lỗi cần ôn, tối đa 5 từ quan trọng và gợi ý một bài luyện tiếp theo. Chỉ dùng những nội dung có trong hội thoại; không bịa thành tích hoặc điểm trình độ. Nếu AI lỗi, vẫn kết thúc và cho xem lại lịch sử.

## FR11 Những tình huống mở rộng

Giai đoạn 3 có nhiệm vụ như giải thích bug, gọi món khi món đã hết và hỏi nhân vật trong một vụ án nhỏ. Mỗi nhiệm vụ có mục tiêu, vai nhân vật và điều kiện kết thúc. Tính năng Biến ngày của bạn thành bài học nhận câu kể tiếng Việt, giúp diễn đạt tiếng Anh rồi hỏi tiếp.

## Bố cục màn hình

Thanh bên gồm Hội thoại, Từ vựng, Ôn tập và Cài đặt. Vùng chính có tin nhắn, thẻ sửa có thể thu gọn, popup tra từ và ô nhập. Các nút chính: Gửi, Giúp tôi, Dịch câu, Xem lỗi và Kết thúc buổi. Micro và Nghe bổ sung ở giai đoạn 2. Popup đóng bằng Escape hoặc bấm ngoài; hỗ trợ bàn phím và không che ô nhập trên màn hình nhỏ.

# 7 Kiến trúc Python và harness

## Lựa chọn triển khai đề xuất

Backend Python với FastAPI; giao diện HTML và CSS render bằng Jinja2, thêm JavaScript nhỏ cho bấm từ, popup, chọn cụm và micro. SQLite lưu local; Pydantic kiểm tra dữ liệu; pytest kiểm thử. Python quản lý nghiệp vụ và AI, JavaScript xử lý tương tác trình duyệt. Không cần React cho MVP.

FastAPI và Jinja2 phù hợp để tách API khỏi UI và làm tương tác chọn từ chính xác. Streamlit có thể dùng cho prototype chat nhanh, nhưng không chọn làm giao diện chính trong spec vì thao tác từ và cụm cần nhiều kiểm soát. Phiên bản thư viện sẽ được khóa khi tạo môi trường.

## Phân chia module

| **Module**           | **Trách nhiệm**                                             |
|----------------------|-------------------------------------------------------------|
| routers              | Nhận request, kiểm tra đầu vào và trả lỗi có cấu trúc.      |
| conversation_service | Quản lý phiên, thứ tự lượt, chế độ học và trạng thái gửi.   |
| harness              | Ghép context, gọi AI, kiểm tra schema và giới hạn vòng sửa. |
| ai_provider          | Adapter Claude thật và fake provider cho demo hoặc test.    |
| vocabulary_service   | Tra nghĩa, cache, lưu từ và ôn tập.                         |
| repositories         | Ghi đọc SQLite bằng truy vấn tham số và transaction.        |
| speech_provider      | STT và TTS ở giai đoạn 2; không phụ thuộc nghiệp vụ chat.   |

## Harness trong dự án này

Harness là phần Python điều phối model. Mỗi lượt nạp cài đặt, nhiệm vụ, 20 tin nhắn gần nhất và bản tóm tắt trước đó; giới hạn context theo token của provider. Prompt tách yêu cầu hệ thống và lời người dùng. AI trả dữ liệu có cấu trúc gồm reply_en, corrections và suggested_words.

Luồng: validate input → lưu lượt pending → build context → gọi provider → validate output → ghi reply và correction trong cùng transaction → trả UI. JSON sai được yêu cầu sửa một lần, tổng tối đa 2 call cho một tác vụ. Nếu vẫn sai, trả trạng thái failed; không hiển thị JSON thô.

Đặt timeout đề xuất 30 giây mỗi call và tối đa 65 giây cho tác vụ; không tự retry mạng liên tục. Khi người dùng thử lại, dùng cùng request_id và không tạo bản sao. Retry có thể phát sinh phí nếu provider đã xử lý lượt trước; hiển thị rõ trạng thái chưa xác định khi cần.

# 8 Dữ liệu và hợp đồng API

## Mô hình dữ liệu tối thiểu

| **Bảng**           | **Các trường chính**                                                                         |
|--------------------|----------------------------------------------------------------------------------------------|
| profiles           | id, level, correction_mode, timezone, reuse_words                                            |
| conversations      | id, profile_id, topic, status, summary, created_at                                           |
| messages           | id, conversation_id, role, original_text, input_mode, status, request_id, created_at         |
| corrections        | id, message_id, category, original_span, corrected_text, explanation_vi, prompt_version      |
| vocabulary         | id, profile_id, lemma, selected_text, meaning_vi, meaning_key, pos, example_en, note, due_at |
| vocabulary_sources | vocabulary_id, message_id, source_sentence, selected_start, selected_end                     |
| review_events      | id, vocabulary_id, outcome, reviewed_at                                                      |
| ai_runs            | id, request_id, operation, provider, model, prompt_version, status, token_usage, duration_ms |

Foreign key bật trong SQLite. request_id unique theo tác vụ; vocabulary unique theo profile_id, lemma và meaning_key đã chuẩn hóa. Offset lựa chọn thống nhất theo chỉ số Unicode code point; frontend chuyển đổi từ UTF16 khi cần. Tất cả timestamp lưu UTC; trình bày và lịch ôn dùng múi giờ cấu hình.

## API nội bộ đề xuất

| **Endpoint**                          | **Hợp đồng chính**                                                                           |
|---------------------------------------|----------------------------------------------------------------------------------------------|
| POST /api/conversations               | Nhận topic, level, correction_mode; trả conversation_id.                                     |
| POST /api/conversations/{id}/messages | Nhận request_id, text, input_mode; trả message, reply, corrections và status.                |
| POST /api/help                        | Nhận conversation_id, level 1 đến 3, intent_vi tùy chọn; trả hint_en và explanation_vi.      |
| POST /api/lookup                      | Nhận message_id, start, end; server lấy câu nguồn và trả meaning_vi, lemma, pos, example_en. |
| GET hoặc POST /api/vocabulary         | GET tìm từ; POST lưu lookup đã xác thực. PATCH sửa, DELETE xóa theo ID.                      |
| POST /api/reviews                     | Nhận vocabulary_id và outcome remembered hoặc again.                                         |
| POST /api/conversations/{id}/finish   | Kết thúc và trả tổng kết.                                                                    |
| POST /api/speech/transcribe           | Giai đoạn 2 nhận audio và language; trả transcript để người dùng duyệt.                      |

Response lỗi dùng code, message_vi và retryable; không lộ key hoặc stack trace. Kiểm tra ID hội thoại và message tồn tại, offset trong phạm vi và đối tượng thuộc profile hiện tại. UI không được gửi lịch sử tùy ý thay thế dữ liệu server.

# 9 Chất lượng vận hành và kiểm thử

## Yêu cầu phi chức năng

- Chạy local trên Windows và macOS qua trình duyệt; mặc định bind 127.0.0.1. Có README, dữ liệu demo và fake provider không cần key.

- Sau thao tác gửi, trạng thái loading xuất hiện dưới 300 ms trên máy phát triển. Mục tiêu phản hồi AI dưới 15 giây trên bộ thử xác định; đo median và p95, không bảo đảm khi provider chậm.

- Giữ dữ liệu sau restart. Xóa hội thoại xóa messages, corrections và liên kết nguồn; từ đã lưu được giữ nhưng bỏ liên kết. Có chức năng Xóa toàn bộ dữ liệu học.

- API key chỉ ở backend qua biến môi trường; không xuất vào HTML, log hoặc Git. Log mặc định chỉ metadata, không ghi câu chat hoặc âm thanh.

- Escape nội dung AI và người dùng khi render; không cho AI thực thi shell, SQL hoặc nội dung HTML. Truy vấn DB dùng tham số.

- Cấu hình model, max output tokens và hạn mức ngày. Đề xuất giới hạn 100 lượt AI/ngày; chi phí chỉ hiển thị khi có bảng giá cấu hình, không suy diễn từ số lượt.

- Gọi API gửi nội dung học đến provider; thông báo trước lần đầu. Triển khai public cần thêm authentication, HTTPS, phân quyền và rate limit.

## Tiêu chí nghiệm thu trọng tâm

| **Mã** | **Tình huống và kết quả đạt**                                                            |
|--------|------------------------------------------------------------------------------------------|
| AC01   | Gửi câu rỗng hoặc quá giới hạn bị chặn; gửi hai lần cùng request_id chỉ có một lượt.     |
| AC02   | Yesterday I go to work được gợi ý went và giải thích quá khứ; ý chính được giữ.          |
| AC03   | Câu đúng không bị gắn lỗi; gợi ý tự nhiên hơn được phân loại riêng.                      |
| AC04   | Chế độ giao tiếp không mở thẻ lỗi ngay; Xem lỗi và tổng kết vẫn truy cập được.           |
| AC05   | book trong hai câu danh từ và động từ cho nghĩa khác nhau; looks after được tra như cụm. |
| AC06   | Lưu cùng từ cùng nghĩa không trùng; khác nghĩa tạo mục riêng; restart vẫn còn dữ liệu.   |
| AC07   | Bấm trợ giúp không tự gửi; người dùng sửa câu mẫu trước khi gửi được.                    |
| AC08   | JSON AI lỗi chỉ sửa một lần; timeout hoặc key sai không làm mất câu nhập.                |
| AC09   | Giai đoạn 2 cho sửa transcript trước gửi; từ chối micro vẫn gõ được.                     |
| AC10   | Thử lại câu sửa chấp nhận cách diễn đạt cùng ý; không bắt khớp chuỗi.                    |

Unit test cho validator, dedup, lịch ôn và context; integration test với fake provider và DB tạm; end to end cho chat, popup từ, lưu và mở lại lịch sử. Dùng tập cố định 30 câu để review chất lượng AI: câu đúng, sai, nhiều nghĩa và trộn Việt Anh. Không assert nguyên văn phản hồi model; tester đánh giá đúng ý, đúng nghĩa và giải thích.

# 10 Kế hoạch xây dựng và bàn giao

## Thứ tự triển khai

| **Mốc**             | **Công việc**                                       | **Kết quả có thể kiểm tra**                         |
|---------------------|-----------------------------------------------------|-----------------------------------------------------|
| 1 Khung dự án       | FastAPI, templates, SQLite, fake provider, cấu hình | Chat giả lập; lịch sử còn sau restart.              |
| 2 Claude và sửa lỗi | Adapter, schema, harness, hai chế độ, trợ giúp      | Chat thật; nhận xét và gợi ý có cấu trúc.           |
| 3 Từ vựng           | Token UI, chọn cụm, lookup ngữ cảnh, cache, lưu từ  | Bấm tra từ; phân biệt book theo câu.                |
| 4 Hoàn thiện MVP    | Ôn thủ công, tổng kết, lỗi API, xóa dữ liệu, test   | Chạy trọn một buổi học và nghiệm thu AC01 đến AC08. |
| 5 Giọng nói         | Micro, STT, transcript, phát giọng, thử lại         | Luồng nói và nghe; nghiệm thu AC09 và AC10.         |
| 6 Cá nhân hóa       | Lịch ôn, lỗi cũ, từ xuất hiện lại, nhiệm vụ         | Buổi sau dùng lại dữ liệu đã học.                   |

Ước lượng học và làm: MVP khoảng 10 đến 15 buổi, mỗi buổi 60 đến 90 phút, tùy nền tảng Python và mức dùng Claude hỗ trợ. Đây là ước lượng kế hoạch, không phải cam kết tiến độ; phần giọng nói được ước lượng sau thử nghiệm provider.

## Cách dùng Claude khi phát triển

Mỗi phiên giao một chức năng nhỏ kèm mã FR và tiêu chí AC. Yêu cầu đọc spec, nêu file sẽ sửa, triển khai và chạy kiểm thử liên quan. Lưu progress.md với việc đã xong, kiểm thử và bước tiếp theo; dùng Git commit sau mỗi mốc chạy được. Không đưa API key vào prompt.

Claude hỗ trợ viết code và Claude được gọi trong ứng dụng là hai vai trò riêng. Phiên phát triển không tự gọi API trả phí để kiểm thử; dùng fake provider trước, sau đó chạy smoke test live có giới hạn. Không cần agent tự sửa code hoặc multi agent cho MVP.

## Điều kiện bàn giao MVP

- Mã nguồn, dependency được khóa phiên bản, .env.example không chứa secret và hướng dẫn Windows hoặc macOS.

- Database khởi tạo được, migration có phiên bản và dữ liệu demo.

- Luồng chat → sửa → tra từ → lưu → ôn → tổng kết hoạt động; test tự động đạt và bảng nghiệm thu có kết quả.

- Thông báo rõ AI có thể sai; cung cấp nút đánh dấu phản hồi cần xem lại.

## Các quyết định trước giai đoạn giọng nói

Chọn dịch vụ STT và phương án TTS theo chất lượng, phí và dữ liệu gửi đi; kiểm tra Chrome trên Windows và Safari trên macOS. Chốt có triển khai public hay chỉ local. Giữ provider adapter để có thể đổi nhà cung cấp mà không sửa nghiệp vụ.

## Tài liệu kỹ thuật tham khảo

FastAPI Templates: https://fastapi.tiangolo.com/advanced/templates/

Claude Messages API: https://platform.claude.com/docs/en/api/http/messages

MDN SpeechRecognition: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition

Anthropic Harness: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
