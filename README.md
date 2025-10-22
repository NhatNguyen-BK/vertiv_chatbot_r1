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

# Chạy giao diện
```bash
python -m src.app.options.gradio
```