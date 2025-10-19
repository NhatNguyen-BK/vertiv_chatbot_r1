# src/ingest/index_qdrant.py
import os
import glob
import hashlib
from typing import List, Dict, Iterable

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    SparseVectorParams,
    SparseIndexParams
)
from fastembed import SparseTextEmbedding

# modules nội bộ
from .schema import DocMeta
from .chunkers import pdf_to_chunks            # ưu tiên PDF qua chunker riêng (giữ page_range)
from .parser import parse_any                  # cho ảnh / excel / csv / md ...

# ============== CẤU HÌNH ==============
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY chưa có. Thêm vào .env")

EMBED_MODEL    = os.getenv("EMBED_MODEL", "text-embedding-3-large")
SPARSE_MODEL   = os.getenv("SPARSE_MODEL", "Qdrant/bm25")  # hoặc "Qdrant/bm42-all-minilm-l6-v2-attentions"
QDRANT_HOST    = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT    = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION     = os.getenv("QDRANT_COLLECTION", "vertiv_docs")  # có thể đặt theo model nếu muốn
DATA_ROOT      = "data"   # sẽ quét: data/<product_line>/<product_name>/*

# tham số chunk
CHUNK_SIZE     = 4096
CHUNK_OVERLAP  = 200
BATCH_EMB      = 64

oa = OpenAI(api_key=OPENAI_API_KEY)
qdrant = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    prefer_grpc=False,
    check_compatibility=False,
)

# Khởi tạo sparse embedding model
sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)

# ============== TIỆN ÍCH ==============
def make_chunks(text: str, max_chars: int, overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    out, n = [], len(text)
    i = 0
    while i < n:
        j = min(i + max_chars, n)
        out.append(text[i:j])
        if j == n:
            break
        i = max(j - overlap, 0)
    return out

def embed_texts(batch: List[str]) -> List[List[float]]:
    """Tạo dense vectors từ OpenAI"""
    resp = oa.embeddings.create(model=EMBED_MODEL, input=batch)
    return [d.embedding for d in resp.data]

def embed_sparse(batch: List[str]) -> List[Dict]:
    """
    Tạo sparse vectors từ fastembed.
    Trả về list of dicts với format: {"indices": [...], "values": [...]}
    """
    sparse_vecs = list(sparse_model.embed(batch))
    result = []
    for vec in sparse_vecs:
        result.append({
            "indices": vec.indices.tolist(),
            "values": vec.values.tolist()
        })
    return result

def ensure_collection(dense_dim: int):
    """
    Tạo collection với cả dense và sparse vectors.
    - Dense vector: "dense" (OpenAI embedding)
    - Sparse vector: "sparse" (BM25 hoặc SPLADE)
    """
    names = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION not in names:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": VectorParams(size=dense_dim, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False,
                    )
                )
            }
        )

def upsert_points(points: Iterable[PointStruct]):
    qdrant.upsert(collection_name=COLLECTION, points=list(points))

def detect_language(path: str) -> str:
    """
    Suy luận ngôn ngữ từ tên file/thư mục (mặc định en).
    Thêm các từ khoá nếu bạn dùng quy ước khác.
    """
    lower = path.lower()
    if any(k in lower for k in ["_vi", "tieng_viet", "huong_dan", "vietnamese", "-vi.", " vi."]):
        return "vi"
    return "en"

def infer_meta_from_path(path: str, doc_type_hint: str | None = None) -> DocMeta:
    """
    Suy luận metadata sản phẩm từ đường dẫn.
    Ví dụ:
        data/DC_Power/netsure_731/netsure_731_a41_brochure.pdf
        data/Thermal/liebert_crv4/liebert_crv4_brochure.pdf
    """
    parts = os.path.normpath(path).split(os.sep)

    # --- Xác định product_line (DC Power, Thermal, UPS)
    product_line = "Unknown"
    for line in ["DC_Power", "Thermal", "UPS"]:
        if line in parts:
            product_line = line.replace("_", " ")
            break

    # --- Xác định product_name
    product_name = os.path.basename(os.path.dirname(path))
    product_name_fmt = product_name.replace("_", " ").title()

    # --- Xác định model (từ tên file)
    fn_lower = os.path.basename(path).lower()
    if "a41" in fn_lower:
        model = "A41"
    elif "crv4" in fn_lower:
        model = "CRV4"
    elif "pex4" in fn_lower:
        model = "PEX4"
    elif "pex3" in fn_lower:
        model = "PEX3"
    elif "exs" in fn_lower:
        model = "EXS"
    else:
        model = product_name.split("_")[-1].upper() if "_" in product_name else ""

    # --- Loại tài liệu
    if doc_type_hint:
        doc_type = doc_type_hint
    elif "manual" in fn_lower:
        doc_type = "manual"
    elif "brochure" in fn_lower:
        doc_type = "brochure"
    else:
        doc_type = "doc"

    # --- Ngôn ngữ
    language = detect_language(path)

    # --- Gắn metadata đầy đủ
    return DocMeta(
        product_line=product_line,
        product_name=product_name_fmt,
        model=model,
        sku=None,
        region=None,
        language=language,
        doc_type=doc_type,
        version=None,
        publish_date=None,
        source=os.path.basename(path),
        page_range=None,
        checksum=None,
    )

# ============== XỬ LÝ 1 FILE ==============
def chunks_for_file(path: str, meta: DocMeta) -> List[Dict]:
    """
    Trả về list {"text":..., "metadata": {...}}.
    - PDF: đi qua pdf_to_chunks (giữ page_range thật)
    - Khác: parse text rồi cắt theo ký tự (page_range giả = thứ tự chunk)
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return pdf_to_chunks(path, meta, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

    # ảnh / excel / csv / md ...
    text = parse_any(path) or ""
    texts = make_chunks(text, CHUNK_SIZE, CHUNK_OVERLAP)
    out = []
    for i, t in enumerate(texts, 1):
        md = meta.model_dump()
        md["page_range"] = [i]
        out.append({"text": t, "metadata": md})
    return out

def index_one_file(path: str):
    meta = infer_meta_from_path(path)
    chunks = chunks_for_file(path, meta)
    if not chunks:
        print(f"⚠️  No text found in {path}")
        return

    texts = [c["text"] for c in chunks]
    
    # Tạo dense vectors (OpenAI embeddings)
    all_dense_vecs: List[List[float]] = []
    for i in range(0, len(texts), BATCH_EMB):
        batch = texts[i:i + BATCH_EMB]
        all_dense_vecs.extend(embed_texts(batch))

    # Tạo sparse vectors (BM25/SPLADE)
    all_sparse_vecs: List[Dict] = []
    for i in range(0, len(texts), BATCH_EMB):
        batch = texts[i:i + BATCH_EMB]
        all_sparse_vecs.extend(embed_sparse(batch))

    ensure_collection(dense_dim=len(all_dense_vecs[0]))

    points: List[PointStruct] = []
    for i, (dense_vec, sparse_vec, ch) in enumerate(zip(all_dense_vecs, all_sparse_vecs, chunks)):
        pid = int(hashlib.md5(f"{path}-{i}".encode()).hexdigest()[:12], 16)
        payload = ch["metadata"] | {"source_text": ch["text"]}
        
        # Tạo point với cả dense và sparse vectors
        points.append(PointStruct(
            id=pid, 
            vector={
                "dense": dense_vec,
                "sparse": sparse_vec
            },
            payload=payload
        ))

    upsert_points(points)
    rel = os.path.relpath(path, DATA_ROOT) if os.path.isdir(DATA_ROOT) else path
    print(f"✅ Indexed {len(points)} chunks from {rel} (dense + sparse vectors)")

# ============== MAIN ==============
def main():
    # các định dạng cần index; bổ sung nếu cần
    exts = ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.xls", "*.xlsx", "*.csv", "*.md", "*.txt"]
    files: List[str] = []
    for e in exts:
        files.extend(glob.glob(os.path.join(DATA_ROOT, "**", e), recursive=True))

    if not files:
        print(f"⚠️  No files under {DATA_ROOT}")
        return

    files.sort()
    for f in files:
        print(f"📄 Indexing {f} ...")
        try:
            index_one_file(f)
        except Exception as e:
            print(f"❌ Skip {f}: {e}")

if __name__ == "__main__":
    main()