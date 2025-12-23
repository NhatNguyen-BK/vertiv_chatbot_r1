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
from .step_4 import get_node_metadata          # dùng LlamaIndex nodes với metadata chi tiết

# Import database modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.database.connect_db import SessionLocal
from src.database import crud

# ============== CẤU HÌNH ==============
load_dotenv()

# BGE-M3 model - hỗ trợ cả dense và sparse vectors
BGE_M3_MODEL = os.getenv("BGE_M3_MODEL", "BAAI/bge-m3")
QDRANT_HOST    = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT    = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION     = os.getenv("QDRANT_COLLECTION", "vertiv_docs1")  # có thể đặt theo model nếu muốn
DATA_ROOT      = "data"   # sẽ quét: data/<product_line>/<product_name>/*
os.environ["LLAMA_CLOUD_API_KEY"] = os.getenv("LLAMA_API_KEY")

# tham số chunk - BGE-M3 max sequence length là 8192 tokens
CHUNK_SIZE     = 4096  # Chunk size tối ưu
CHUNK_OVERLAP  = 150
BATCH_EMB      = 2    # Giảm batch size do model nặng hơn

# Giới hạn chunk size cho BGE-M3 (8192 tokens ~ 6000-7000 chars)
MIN_CHUNK_CHARS = 1024    # Chunks nhỏ hơn sẽ được merge
MAX_CHUNK_CHARS = 7000  # Chunks lớn hơn sẽ được split (giới hạn BGE-M3)

# Khởi tạo BGE-M3 model (hỗ trợ cả dense, sparse)
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
def embed_texts_bge_m3(batch: List[str]) -> tuple[List[List[float]], List[Dict]]:
    """
    Tạo cả dense và sparse vectors từ BGE-M3.
    Trả về:
        - dense_vectors: List[List[float]] - dense embeddings (1024 dim)
        - sparse_vectors: List[Dict] - sparse embeddings với format {"indices": [...], "values": [...]}
    """
    # Truncate text nếu quá dài (BGE-M3 max_length = 8192 tokens ~ 6000 chars)
    truncated_batch = []
    for text in batch:
        if len(text) > 5000:  # An toàn hơn, giới hạn 5000 chars
            truncated_batch.append(text[:5000])
        else:
            truncated_batch.append(text)
    
    # BGE-M3 encode với cả dense và sparse
    embeddings = bge_m3_model.encode(
        truncated_batch, 
        return_dense=True, 
        return_sparse=True,
        return_colbert_vecs=False,  # Không cần colbert cho use case này
        max_length=8192  # BGE-M3 max sequence length
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


def extract_header(text: str) -> str:
    """
    Trích xuất header (heading) từ đầu chunk.
    Tìm các dòng bắt đầu bằng # hoặc ##
    """
    lines = text.strip().split('\n')
    headers = []
    for line in lines[:5]:  # Chỉ kiểm tra 5 dòng đầu
        line = line.strip()
        if line.startswith('#'):
            headers.append(line)
        elif headers:  # Đã có header rồi, dừng lại
            break
    return '\n'.join(headers) if headers else ""


def split_large_chunk(chunk: Dict, max_chars: int = MAX_CHUNK_CHARS) -> List[Dict]:
    """
    Tách chunk lớn thành các chunks nhỏ hơn, giữ header gốc.
    """
    text = chunk["text"]
    metadata = chunk["metadata"]
    
    if len(text) <= max_chars:
        return [chunk]
    
    # Trích xuất header
    header = extract_header(text)
    header_len = len(header) + 2 if header else 0  # +2 cho \n\n
    
    # Tính max size cho content
    content_max = max_chars - header_len
    if content_max < 100:
        content_max = max_chars  # Fallback nếu header quá dài
        header = ""
    
    # Loại bỏ header khỏi text để tách
    content = text
    if header:
        content = text[len(header):].strip()
    
    # Tách content thành các phần
    result = []
    i = 0
    part_idx = 0
    while i < len(content):
        end = min(i + content_max, len(content))
        
        # Tìm điểm ngắt tốt (cuối câu, xuống dòng)
        if end < len(content):
            # Tìm ngược lại để tìm điểm ngắt
            for sep in ['\n\n', '\n', '. ', ', ', ' ']:
                pos = content.rfind(sep, i, end)
                if pos > i + content_max // 2:  # Phải ngắt ở ít nhất 50% chunk
                    end = pos + len(sep)
                    break
        
        chunk_text = content[i:end].strip()
        if chunk_text:
            # Thêm header vào đầu mỗi chunk con
            if header and part_idx > 0:
                chunk_text = f"{header}\n\n{chunk_text}"
            elif header and part_idx == 0:
                chunk_text = f"{header}\n\n{chunk_text}"
            
            new_metadata = metadata.copy()
            new_metadata["chunk_part"] = part_idx
            result.append({
                "text": chunk_text,
                "metadata": new_metadata
            })
            part_idx += 1
        
        i = end
    
    return result if result else [chunk]


def merge_small_chunks(chunks: List[Dict], min_chars: int = MIN_CHUNK_CHARS, max_chars: int = MAX_CHUNK_CHARS) -> List[Dict]:
    """
    Merge các chunks nhỏ (< min_chars) vào chunk tiếp theo.
    Xử lý các trường hợp:
    - Chunk < min_chars: merge với chunk tiếp
    - Sau khi merge vẫn < min_chars: tiếp tục merge
    - Sau khi merge > max_chars: giữ chunk hiện tại, bắt đầu chunk mới
    """
    if not chunks:
        return chunks
    
    result = []
    accumulated_text = ""
    accumulated_metadata = None
    
    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        metadata = chunk["metadata"]
        
        # Thêm text vào accumulator
        if accumulated_text:
            combined = accumulated_text + "\n\n" + text
        else:
            combined = text
            accumulated_metadata = metadata
        
        # Kiểm tra kích thước combined
        combined_len = len(combined)
        is_last = (i == len(chunks) - 1)
        
        # Quyết định xử lý combined
        if combined_len >= min_chars and combined_len <= max_chars:
            # Đủ điều kiện: >= min và <= max
            result.append({
                "text": combined,
                "metadata": accumulated_metadata
            })
            accumulated_text = ""
            accumulated_metadata = None
        elif combined_len > max_chars:
            # Quá lớn: lưu chunk trước đó (nếu có) và bắt đầu mới với chunk hiện tại
            if accumulated_text and len(accumulated_text) >= min_chars:
                result.append({
                    "text": accumulated_text,
                    "metadata": accumulated_metadata
                })
            elif accumulated_text:
                # accumulated_text < min_chars nhưng không thể merge thêm (vì quá max)
                # Buộc phải thêm vào result
                result.append({
                    "text": accumulated_text,
                    "metadata": accumulated_metadata
                })
            
            # Bắt đầu mới với chunk hiện tại
            accumulated_text = text
            accumulated_metadata = metadata
        else:
            # combined_len < min_chars: tiếp tục accumulate
            accumulated_text = combined
            
            # Nếu là chunk cuối cùng, buộc phải thêm vào
            if is_last:
                result.append({
                    "text": accumulated_text,
                    "metadata": accumulated_metadata
                })
                accumulated_text = ""
    
    # Xử lý phần còn lại nếu có
    if accumulated_text:
        if result and len(accumulated_text) < min_chars:
            # Nối vào chunk cuối nếu quá nhỏ
            last_combined = result[-1]["text"] + "\n\n" + accumulated_text
            if len(last_combined) <= max_chars:
                result[-1]["text"] = last_combined
            else:
                # Không thể merge vào cuối (quá max), thêm riêng dù nhỏ
                result.append({
                    "text": accumulated_text,
                    "metadata": accumulated_metadata
                })
        else:
            # Thêm vào kết quả
            result.append({
                "text": accumulated_text,
                "metadata": accumulated_metadata
            })
    
    return result


def process_chunks_for_bge_m3(chunks: List[Dict]) -> List[Dict]:
    """
    Xử lý chunks cho BGE-M3:
    1. Merge chunks < 70 ký tự vào chunk tiếp theo (xử lý cả TH merge vẫn < 70 hoặc > max)
    2. Split chunks > 8192 ký tự, giữ header
    """
    # Bước 1: Merge small chunks (xử lý đầy đủ các edge cases)
    merged = merge_small_chunks(chunks, MIN_CHUNK_CHARS, MAX_CHUNK_CHARS)
    
    # Bước 2: Split large chunks (chunks > MAX_CHUNK_CHARS)
    result = []
    for chunk in merged:
        split_chunks = split_large_chunk(chunk, MAX_CHUNK_CHARS)
        result.extend(split_chunks)
    
    return result

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

    # Xử lý chunks cho BGE-M3: merge small, split large
    print(f"📊 Processing {len(chunks)} raw chunks...")
    chunks = process_chunks_for_bge_m3(chunks)
    print(f"📊 After processing: {len(chunks)} chunks (merged small, split large)")

    # Lưu chunks cuối cùng vào file để debug
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    file_name = os.path.splitext(os.path.basename(path))[0]
    output_file = f"{output_dir}/{file_name}_final_chunks.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# File: {os.path.basename(path)}\n")
        f.write(f"# Total Chunks: {len(chunks)}\n\n")
        for idx, chunk in enumerate(chunks, 1):
            f.write(f"# Chunk {idx}\n")
            f.write(chunk['text'])
            f.write("\n\n" + "="*80 + "\n\n")
    print(f"💾 Saved {len(chunks)} final chunks to {output_file}")

    texts = [c["text"] for c in chunks]
    
    # Tạo cả dense và sparse vectors từ BGE-M3 trong một lần
    print(f"🔄 Creating embeddings for {len(texts)} chunks...")
    all_dense_vecs: List[List[float]] = []
    all_sparse_vecs: List[Dict] = []
    
    try:
        total_batches = (len(texts) + BATCH_EMB - 1) // BATCH_EMB
        import time
        for batch_idx, i in enumerate(range(0, len(texts), BATCH_EMB), 1):
            batch = texts[i:i + BATCH_EMB]
            start_time = time.time()
            print(f"  ⏳ Batch {batch_idx}/{total_batches} ({len(batch)} chunks)...", end=" ", flush=True)
            dense_batch, sparse_batch = embed_texts_bge_m3(batch)
            all_dense_vecs.extend(dense_batch)
            all_sparse_vecs.extend(sparse_batch)
            elapsed = time.time() - start_time
            print(f"✅ Done in {elapsed:.1f}s")
        print(f"✅ Created embeddings for {len(all_dense_vecs)} chunks")
    except Exception as e:
        print(f"❌ Error creating embeddings: {e}")
        import traceback
        traceback.print_exc()
        return 0

    ensure_collection(dense_dim=len(all_dense_vecs[0]))

    print(f"🔄 Creating {len(chunks)} points for Qdrant...")
    points: List[PointStruct] = []
    try:
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
        print(f"✅ Created {len(points)} points")
    except Exception as e:
        print(f"❌ Error creating points: {e}")
        import traceback
        traceback.print_exc()
        return 0

    try:
        print(f"🔄 Upserting {len(points)} points to Qdrant...")
        upsert_points(points)
        rel = os.path.relpath(path, DATA_ROOT) if os.path.isdir(DATA_ROOT) else path
        print(f"✅ Indexed {len(points)} chunks from {rel} (BGE-M3 dense + sparse vectors)")
    except Exception as e:
        print(f"❌ Error upserting to Qdrant: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    # Lưu thông tin vào database (trừ khi skip_db=True)
    if not skip_db:
        try:
            save_to_database(path, meta, len(points))
        except Exception as e:
            print(f"⚠️  Warning: Could not save to database: {e}")
    
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