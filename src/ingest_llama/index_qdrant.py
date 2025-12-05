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
from .step_4 import get_node_metadata          # dùng LlamaIndex nodes với metadata chi tiết

# Import database modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.database.connect_db import SessionLocal
from src.database import crud

# ============== CẤU HÌNH ==============
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY chưa có. Thêm vào .env")

EMBED_MODEL    = os.getenv("EMBED_MODEL", "text-embedding-3-large")
SPARSE_MODEL   = os.getenv("SPARSE_MODEL", "Qdrant/bm25")  # hoặc "Qdrant/bm42-all-minilm-l6-v2-attentions"
QDRANT_HOST    = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT    = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION     = os.getenv("QDRANT_COLLECTION", "vertiv_docs1")  # có thể đặt theo model nếu muốn
DATA_ROOT      = "data"   # sẽ quét: data/<product_line>/<product_name>/*
os.environ["LLAMA_CLOUD_API_KEY"] = os.getenv("LLAMA_API_KEY")
# tham số chunk
CHUNK_SIZE     = 4096
CHUNK_OVERLAP  = 200
BATCH_EMB      = 64

oa = OpenAI()
qdrant = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    prefer_grpc=False,
    check_compatibility=False,
)

# Khởi tạo sparse embedding model
sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)

# ============== TIỆN ÍCH ==============
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

# ============== DATABASE HELPER ==============
def save_to_database(path: str, meta: DocMeta, num_chunks: int):
    """
    Lưu thông tin file đã index vào database
    """
    db = SessionLocal()
    try:
        # Chuẩn hóa category_id và product_line_id
        category_name = meta.product_line  # "DC Power", "Thermal", "UPS"
        category_id = category_name.lower().replace(" ", "_")  # "dc_power", "thermal", "ups"
        
        # Tạo hoặc lấy Category
        category = crud.get_or_create_category(
            db, 
            id=category_id, 
            name=category_name
        )
        
        # Chuẩn hóa product_line_id (tên sản phẩm chính, vd: "Netsure 731", "Liebert CRV")
        # Lấy phần đầu của product_name (trước số model)
        product_line_name = meta.product_name
        product_line_id = product_line_name.lower().replace(" ", "_")
        
        # Tạo hoặc lấy ProductLine
        product_line = crud.get_or_create_product_line(
            db,
            id=product_line_id,
            name=product_line_name,
            category_id=category_id
        )
        
        # Tạo product_id từ model hoặc product_name
        product_name = meta.model if meta.model else product_line_name
        product_id = f"{product_line_id}_{meta.model.lower()}" if meta.model else product_line_id
        
        # Tạo hoặc lấy Product
        product = crud.get_or_create_product(
            db,
            id=product_id,
            name=product_name,
            product_line_id=product_line_id
        )
        
        # Tạo file_id từ checksum hoặc hash của path
        file_name = os.path.basename(path)
        file_id = hashlib.md5(path.encode()).hexdigest()[:16]
        
        # Tạo hoặc lấy File
        file = crud.get_or_create_file(
            db,
            id=file_id,
            name=file_name,
            product_id=product_id
        )
        
        print(f"✅ Saved to DB: {category_name} > {product_line_name} > {product_name} > {file_name} ({num_chunks} chunks)")
        
    except Exception as e:
        print(f"⚠️  Error saving to DB for {path}: {e}")
        db.rollback()
    finally:
        db.close()


# ============== XỬ LÝ 1 FILE ==============
def get_chunks_from_pdf(path: str, meta: DocMeta) -> List[Dict]:
    """
    Dùng step_4 để lấy documents từ PDF với metadata chi tiết 
    (page tracking, heading context, etc).
    Trả về list {"text": str, "metadata": dict} tương thích với index flow.
    """
    try:
        documents = get_node_metadata(path)
        if not documents:
            return []
        
        out = []
        for doc in documents:
            # Document từ step_4 có text và metadata
            # Merge metadata từ DocMeta + document.metadata từ step_4
            merged_meta = meta.model_dump()
            if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
                # Lấy page từ step_4 metadata
                if 'page' in doc.metadata:
                    merged_meta['page_range'] = [doc.metadata['page']]
                # Cập nhật các metadata khác từ step_4 nếu có
                merged_meta.update({k: v for k, v in doc.metadata.items() if k != 'page_range'})
            
            out.append({
                "text": doc.text if hasattr(doc, 'text') else str(doc),
                "metadata": merged_meta
            })
        return out
    except Exception as e:
        print(f"⚠️  Error in get_chunks_from_pdf for {path}: {e}")
        return []

def index_one_file(path: str, skip_db: bool = False):
    """
    Index một file PDF vào Qdrant
    
    Args:
        path: Đường dẫn đến file PDF
        skip_db: Nếu True, không lưu vào database (dùng khi gọi từ upload API)
    
    Returns:
        Số chunks đã index, hoặc 0 nếu thất bại
    """
    # Chỉ xử lý PDF
    ext = os.path.splitext(path)[1].lower()
    if ext != ".pdf":
        print(f"⏭️  Skip {path} (chỉ hỗ trợ PDF)")
        return 0
    
    meta = infer_meta_from_path(path)
    chunks = get_chunks_from_pdf(path, meta)
    if not chunks:
        print(f"⚠️  No text found in {path}")
        return 0

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
    
    # Lưu thông tin vào database (trừ khi skip_db=True)
    if not skip_db:
        save_to_database(path, meta, len(points))
    
    return len(points)

# ============== MAIN ==============
def main():
    # Chỉ xử lý PDF files
    exts = ["*.pdf"]
    files: List[str] = []
    for e in exts:
        files.extend(glob.glob(os.path.join(DATA_ROOT, "**", e), recursive=True))

    if not files:
        print(f"⚠️  No PDF files under {DATA_ROOT}")
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