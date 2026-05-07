# RAG Chunking Demo (FastAPI)

Source code nay bam sat `Prepare.md`:

- Parse `.docx` thanh cac block co metadata
- Chunk theo 3 chien luoc: `fixed`, `overlap`, `semantic`
- Luu metadata vao SQLite
- Luu embeddings vao Chroma
- Query `topK`, `threshold`, va tra ve `distance + similarity`

## 1) Cai dat

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Tao file `.env` tu `.env.example`.

Ban co 2 cach cau hinh embedding:

- OpenAI API: dien `OPENAI_API_KEY`.
- Azure OpenAI: dien `OPENAI_ENDPOINT`, `OPENAI_KEY`, `OPENAI_EMBEDDING_DEPLOYMENT`.

Luu y: `OPENAI_DEPLOYMENT=gpt-4o` la cho chat model, khong dung de tao embedding.
Neu gap 429 rate limit embedding, giam `EMBEDDING_BATCH_SIZE` (vd 10) va tang retry trong `.env`.

## 2) Chay API

```bash
uvicorn src.main:app --reload --port 8010
```

Docs: <http://localhost:8010/swagger>

## 2.1) Mini UI (Streamlit)

```bash
streamlit run streamlit_app.py
```

Mini UI cho phep:
- Query va so sanh ket qua retrieval giua `fixed | overlap | semantic`
- Hien thi `similarity`, `distance`, va raw chunk text theo tung strategy

### Chay UI de xem du lieu Chroma (compare)

UI nay la man hinh de query cac chunk da embedding trong Chroma va so sanh 3 chien luoc chunking.

```bash
streamlit run streamlit_app.py
```

Neu lenh `streamlit` khong nhan, dung:

```bash
python -m streamlit run streamlit_app.py
```

## 3) API chinh

### 3.1 `POST /extract` - Upload va extract DOCX vao SQLite

Y nghia:
- Nhan file `.docx`, parse thanh cac block (`heading`, `paragraph`, `list_item`, `table`)
- Luu block tho + metadata vao bang `extracted_blocks` trong SQLite
- Tra ve `doc_id` de dung cho buoc `/index`

Cach dung:
- Content-Type: `multipart/form-data`
- Field bat buoc:
  - `file`: file `.docx`

Ket qua:
- `doc_id`: ID tai lieu vua extract
- `total_blocks`: tong so block da luu vao SQLite

### 3.2 `POST /index` - Chunk + embedding + upsert vao Chroma

Y nghia:
- Lay du lieu da extract trong SQLite theo `doc_id`
- Thuc hien chunk theo strategy
- Tao embedding va luu vao collection Chroma tuong ung

Cach dung:
- Content-Type: `application/json`
- Payload bat buoc chung:
  - `doc_id`
  - `strategy`

Payload chi tiet theo strategy:

- Fixed (can `chunk_size`):

```json
{
  "doc_id": "6811322529b2",
  "strategy": "fixed",
  "chunk_size": 500
}
```

- Overlap (can `chunk_size` + `overlap`, voi `overlap < chunk_size`):

```json
{
  "doc_id": "6811322529b2",
  "strategy": "overlap",
  "chunk_size": 500,
  "overlap": 100
}
```

- Semantic (chi can `doc_id` + `strategy`):

```json
{
  "doc_id": "6811322529b2",
  "strategy": "semantic"
}
```

Ket qua:
- `doc_id`, `strategy`
- `total_blocks`, `total_chunks`
- `collection` (vi du `word_docs_fixed`)

### 3.3 `POST /query` - Tim chunk lien quan trong Chroma

Y nghia:
- Nhan cau hoi (`query`) va strategy can tim
- Query vector trong Chroma collection tuong ung
- Tra ve danh sach ket qua kem `distance` va `similarity`

Cach dung:
- Content-Type: `application/json`
- Truyen:
  - `query`: noi dung can tim
  - `strategy`: `fixed | overlap | semantic`
  - `top_k`: so ket qua toi da muon lay
  - `threshold` (optional): nguong similarity toi thieu
  - `doc_id` (optional): loc ket qua theo tai lieu

Vi du:

```json
{
  "query": "Dieu kien thanh toan gom nhung gi?",
  "strategy": "overlap",
  "top_k": 5,
  "threshold": 0.75
}
```

Luu y:
- `top_k` = lay toi da K ket qua gan nhat
- `threshold` = loc ket qua co `similarity >= threshold`
- Neu dat threshold cao, `total_returned` co the < `top_k`

- `GET /debug/chroma/collections`
- `GET /debug/chroma/peek?strategy=semantic&limit=5`
- `DELETE /admin/clear-data` (xoa sach du lieu trong SQLite + toan bo Chroma collections)

## 4) Luu y demo

- Chroma duoc tach collection theo strategy: `word_docs_<strategy>`.
- SQLite chi dung 1 bang `extracted_blocks` de luu block thô sau khi parse file.
- Chunk sau khi `/index` duoc tao runtime va dua thang vao Chroma collection.
- Neu doi embedding model, nen tao collection moi va ingest lai.
