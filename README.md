# Sử dụng python 3.12
# Chạy thư viện
```bash
pip install -r requirements.txt
```

# Chunk và lưu dữ liệu vào QDRANT
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

