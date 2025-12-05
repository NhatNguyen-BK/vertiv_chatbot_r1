# Sử dụng python 3.12
# Chạy thư viện
```bash
pip install -r requirements.txt
```

# Chunk và lưu dữ liệu vào QDRANT
```bash
pip install --pre chunkr-ai
```
```bash
python -m src.ingest.index_qdrant
```

# Chunk và lưu dữ liệu bằng markdown
```bash
python -m src.ingest_llama.index_qdrant
```

# Chạy backend
```bash
uvicorn src.app.server:app --reload --port 8000
```

# Chạy giao diện FE
1. Vào thư mục giao diện
```bash
cd frontend
```
2. Thêm 1 folder public/docs và thêm tất cả các file pdf vào thư mục này
3. Chạy tiếp các lệnh sau
```bash
npm install
npm run dev
```

# Chạy docker
```php
docker run --name vertiv-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres123 \
  -e POSTGRES_DB=vertiv_docs \
  -p 5432:5432 \
  -v vertiv_pgdata:/var/lib/postgresql/data \
  -d postgres:15
```

```php
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

