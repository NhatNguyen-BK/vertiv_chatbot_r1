# Chạy thư viện
```bash
pip install -r requirements.txt
```

# Chạy thư viện parser
## Bước 1: 
```bash
git clone https://github.com/microsoft/markitdown.git
```
## Bước 2:
```bash
cd markitdown
```
## Bước 3:
```bash
pip install -e packages/markitdown[all]
```
# Chunk và lưu dữ liệu vào QDRANT
```bash
python -m src.ingest.index_qdrant
```

# Chạy giao diện
```bash
python -m src.app.options.gradio
```