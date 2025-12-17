# src/ingest/index_qdrant.py
import os
import glob
import hashlib
from typing import List, Dict, Iterable

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    SparseVectorParams,
    SparseIndexParams
)
from FlagEmbedding import BGEM3FlagModel

# modules nội bộ
from .schema import DocMeta
from .chunkers import pdf_to_chunks            # ưu tiên PDF qua chunker riêng (giữ page_range)
from .parser import parse_any                  # cho ảnh / excel / csv / md ...

# ============== CẤU HÌNH ==============
load_dotenv()

# BGE-M3 model - hỗ trợ cả dense và sparse vectors
BGE_M3_MODEL = os.getenv("BGE_M3_MODEL", "BAAI/bge-m3")
QDRANT_HOST    = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT    = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION     = os.getenv("QDRANT_COLLECTION", "vertiv_docs")  # có thể đặt theo model nếu muốn
DATA_ROOT      = "data"   # sẽ quét: data/<product_line>/<product_name>/*

# tham số chunk - BGE-M3 max sequence length là 8192, nhưng optimal là 1024
CHUNK_SIZE     = 1024  # Giảm xuống 1024 tokens cho BGE-M3
CHUNK_OVERLAP  = 150
BATCH_EMB      = 32    # Giảm batch size do model nặng hơn

# Khởi tạo BGE-M3 model (hỗ trợ cả dense, sparse và colbert)
print("🔄 Loading BGE-M3 model...")
bge_m3_model = BGEM3FlagModel(BGE_M3_MODEL, use_fp16=True)
print("✅ BGE-M3 model loaded successfully!")

qdrant = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    prefer_grpc=False,
    check_compatibility=False,
)

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

def embed_texts_bge_m3(batch: List[str]) -> tuple[List[List[float]], List[Dict]]:
    """
    Tạo cả dense và sparse vectors từ BGE-M3.
    Trả về:
        - dense_vectors: List[List[float]] - dense embeddings (1024 dim)
        - sparse_vectors: List[Dict] - sparse embeddings với format {"indices": [...], "values": [...]}
    """
    # BGE-M3 encode với cả dense và sparse
    embeddings = bge_m3_model.encode(
        batch, 
        return_dense=True, 
        return_sparse=True,
        return_colbert_vecs=False  # Không cần colbert cho use case này
    )
    
    dense_vectors = embeddings['dense_vecs'].tolist()
    
    # Xử lý sparse vectors
    sparse_vectors = []
    lexical_weights = embeddings['lexical_weights']
    
    for weights in lexical_weights:
        # weights là dict với token_id -> weight
        indices = list(weights.keys())
        values = list(weights.values())
        sparse_vectors.append({
            "indices": [int(idx) for idx in indices],
            "values": [float(val) for val in values]
        })
    
    return dense_vectors, sparse_vectors

def ensure_collection(dense_dim: int):
    """
    Tạo collection với cả dense và sparse vectors.
    - Dense vector: "dense" (BGE-M3 dense embedding, 1024 dim)
    - Sparse vector: "sparse" (BGE-M3 lexical weights)
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
    
    # Tạo cả dense và sparse vectors từ BGE-M3 trong một lần
    all_dense_vecs: List[List[float]] = []
    all_sparse_vecs: List[Dict] = []
    
    for i in range(0, len(texts), BATCH_EMB):
        batch = texts[i:i + BATCH_EMB]
        dense_batch, sparse_batch = embed_texts_bge_m3(batch)
        all_dense_vecs.extend(dense_batch)
        all_sparse_vecs.extend(sparse_batch)

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
    print(f"✅ Indexed {len(points)} chunks from {rel} (BGE-M3 dense + sparse vectors)")

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