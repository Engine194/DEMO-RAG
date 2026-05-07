## Plan thực hiện demo RAG 

## 1) Chuẩn bị file input

- **Định dạng ưu tiên**: `.docx` (nếu `.doc` thì convert sang `.docx` trước).
- **Nội dung cần có để test chunking tốt**:
  - Có **heading nhiều cấp** (H1/H2/H3).
  - Có **paragraph dài/ngắn xen kẽ**.
  - Có **bullet/list** (cha-con).
  - Có **table** (2 cột và nhiều cột).
- **Yêu cầu chất lượng file**:
  - Không scan ảnh thuần (nếu scan thì phải OCR trước).
  - Hạn chế header/footer lặp quá nhiều.
  - Text Unicode tiếng Việt rõ, không lỗi font.

---

## 2) Design DB

### Bảng `chunks` (SQLite)

- `id` - `INTEGER PK` - khóa chính.
- `doc_id` - `TEXT` - định danh tài liệu.
- `source_file` - `TEXT` - tên file nguồn.
- `chunk_text` - `TEXT` - nội dung chunk để hiển thị/debug.
- `heading_path` - `TEXT` (JSON string) - ngữ cảnh section (H1>H2>H3).
- `block_type` - `TEXT` - loại block (`heading/paragraph/list_item/table`).
- `heading_level` - `INTEGER` - cấp heading nếu có.
- `block_index` - `INTEGER` - thứ tự block trước khi chunk.
- `chunk_index` - `INTEGER` - thứ tự chunk sau khi split.
- `token_count` - `INTEGER` - số token ước lượng.
- `metadata_json` - `TEXT` - full metadata mở rộng.

### Vector DB (Chroma)

- `collection`: `word_docs`
- Lưu:
  - `embedding vector`
  - `document text` (chunk đã chuẩn hóa)
  - `metadata` (`doc_id`, `source_file`, `heading_path`, `block_type`, `chunk_index`...)

---

## 3) Base code

- `src/docx_loader.py`: parse Word thành block có metadata.
- `src/extract_to_sqlite.py`: extract-only vào SQLite (không embedding).
- `src/ingest.py`: chunk + embedding + upsert Chroma + save SQLite.
- `src/query.py`: query topK từ Chroma, in score + metadata.
- `.env`: cấu hình Azure OpenAI/OpenAI.
- `requirements.txt`: langchain + chroma + python-docx + dotenv.

---

## 4) Xây dựng flow cho 2 luồng cơ bản

### Luồng 1: Upload file -> Chunk -> Embedding

- Nhận file `.docx`.
- Parse block (`heading/paragraph/list/table`).
- Chuẩn hóa text (flatten table, clean whitespace, giữ heading_path).
- Chunk theo 3 kỹ thuật để so sánh:
  - **Fixed-size**: chia đều theo độ dài (`chunk_size` cố định).
  - **Fixed + Overlap**: fixed-size + `overlap` để giảm mất ngữ cảnh.
  - **Semantic chunking**: cắt theo `heading/paragraph/meaning`.
- Embedding theo chunk.
- Lưu SQLite + Chroma.
- Log số block/chunk, lỗi rate limit, retry.

### Luồng 2: Search tài liệu

- Nhận query keyword/câu hỏi.
- Tạo query embedding.
- Search vector trong Chroma.
- Trả về `topK` chunks + score + metadata.
- (Optional) rerank + threshold.
- Ghép answer cuối từ chunks.

### Các cách search cần liệt kê

- **Keyword search**: SQL `LIKE`/FTS (nhanh, exact term).
- **Vector search**: semantic similarity (ý nghĩa).
- **Hybrid search**: keyword + vector (khuyến nghị).
- **TopK** vs **Threshold** vs **TopK + Threshold**.
- **Rerank** (optional) để tăng precision.

---

## 5) Tạo testcase để check từng kỹ thuật trong 2 luồng

### Test luồng 1

- Parse đúng block type (heading/list/table/paragraph).
- Paragraph dài được split đúng, không mất ngữ cảnh.
- Table flatten đúng format.
- Metadata đầy đủ, không null trường quan trọng.
- Ingest idempotent (chạy lại không lỗi logic).

### Test luồng 2

- Query keyword trả đúng chunk có từ khóa.
- Query semantic trả đúng section dù khác từ.
- So sánh chunking strategy (fixed/overlap/semantic).
- Test topK/threshold khác nhau cho cùng query.
- Test câu hỏi khó (điều kiện/ngoại lệ/con số).

---

## 6) Làm tài liệu flow thuyết trình

- **Slide 1**: Mục tiêu demo (không chỉ chat tài liệu).
- **Slide 2**: Kiến trúc tổng quan.
- **Slide 3**: Input + parse + metadata.
- **Slide 4**: Chunking strategy so sánh.
- **Slide 5**: Embedding + Vector DB.
- **Slide 6**: Search flow + các mode search.
- **Slide 7**: Kết quả test + lesson learned.
- **Slide 8**: Kết luận + hướng mở rộng.

