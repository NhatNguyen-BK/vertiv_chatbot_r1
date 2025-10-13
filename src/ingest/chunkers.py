# src/ingest/chunkers.py
from typing import List, Dict
from .schema import DocMeta
from .parser import parse_any

def file_to_chunks(
    path: str,
    meta: DocMeta,
    max_chars: int = 1200,
    overlap: int = 150
) -> List[Dict]:
    """
    Đọc file (PDF / Excel / CSV / Ảnh OCR) -> text (parser),
    sau đó chia text thành các chunk có overlap và gắn metadata.
    Trả về: List[{"text": str, "metadata": dict}]
    """
    text = (parse_any(path) or "").strip()
    if not text:
        return []

    chunks: List[Dict] = []
    start = 0
    L = len(text)

    while start < L:
        end = min(start + max_chars, L)
        chunk_text = text[start:end]

        # Gắn metadata (giữ nguyên schema DocMeta)
        payload = meta.model_dump()
        # Vì parser trả về 1 chuỗi hợp nhất, đặt page_range = [1]
        payload["page_range"] = [1]

        chunks.append({"text": chunk_text, "metadata": payload})

        # Tính overlap an toàn
        if end == L:
            break
        start = max(0, end - overlap)

    return chunks

# Giữ alias cho tương thích ngược với code cũ
def pdf_to_chunks(path: str, meta: DocMeta, max_chars: int = 1200, overlap: int = 150) -> List[Dict]:
    return file_to_chunks(path, meta, max_chars=max_chars, overlap=overlap)