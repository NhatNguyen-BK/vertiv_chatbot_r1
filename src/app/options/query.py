# src/app/query.py
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, QueryRequest
from openai import OpenAI
import os
from openai import OpenAI
import os
from dotenv import load_dotenv
from fastembed import SparseTextEmbedding

load_dotenv()

# Import tools mới
from .tools import route_query

oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")
SPARSE_MODEL = os.getenv("SPARSE_MODEL", "Qdrant/bm25")
GEN_MODEL   = os.getenv("GEN_MODEL", "gpt-4o-mini")

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Khởi tạo sparse embedding model
sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)

def _embed(text: str):
    """Tạo dense vector từ OpenAI"""
    e = oa.embeddings.create(model=EMBED_MODEL, input=[text])
    return e.data[0].embedding

def _embed_sparse(text: str):
    """Tạo sparse vector từ fastembed"""
    sparse_vec = list(sparse_model.embed([text]))[0]
    return {
        "indices": sparse_vec.indices.tolist(),
        "values": sparse_vec.values.tolist()
    }

def answer(query: str, product_name: str | None = None):
    # ===== BƯỚC 1: Routing - kiểm tra loại câu hỏi =====
    route_result = route_query(query)
    
    # Nếu là small talk hoặc catalog query, trả về ngay
    if route_result["tool"] in ["small_talk", "catalog"]:
        response = route_result["response"]
        sources = route_result.get("sources", [])
        return response, sources
    
    # ===== BƯỚC 2: RAG - tìm kiếm trong Qdrant =====
    return _rag_answer(query, product_name)

def _rag_answer(query: str, product_name: str | None = None):
    # 1) Lấy vector câu hỏi (dense và sparse)
    dense_vec = _embed(query)
    sparse_vec = _embed_sparse(query)

    # 2) Hybrid search trong Qdrant (kết hợp dense + sparse)
    # Sử dụng prefetch để tìm riêng rồi kết hợp
    search_params = {
        "collection_name": "vertiv_docs",
        "prefetch": [
            Prefetch(
                query=dense_vec,
                using="dense",
                limit=10
            ),
            Prefetch(
                query=sparse_vec,
                using="sparse",
                limit=10
            )
        ],
        "query": dense_vec,  # Fusion vector để re-rank
        "using": "dense",
        "limit": 5,
    }
    
    # Thêm filter nếu có product_name
    if product_name:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="product_name",
                    match=MatchValue(value=product_name)
                )
            ]
        )
        # Thêm filter vào cả prefetch
        search_params["prefetch"][0].filter = query_filter
        search_params["prefetch"][1].filter = query_filter
        search_params["query_filter"] = query_filter  # Đổi từ "filter" thành "query_filter"
    
    hits = client.query_points(**search_params).points
    print("sssssssssssssss: ", hits)
    # 3) Gom ngữ cảnh & nguồn
    contexts = []
    sources = []  # list[str] để hiển thị
    for h in hits:
        p = h.payload or {}
        meta = p.get("metadata", {})  # nếu lúc upsert bạn gộp metadata vào payload
        # tùy vào cách bạn lưu, thử theo 2 key phổ biến:
        src = meta.get("source") or p.get("source") or "unknown.pdf"
        pages = meta.get("page_range") or p.get("page_range")
        page_str = ""
        if isinstance(pages, list) and pages:
            page_str = f" (trang {pages[0]})"
        contexts.append(p.get("source_text", ""))  # phần text gốc để làm RAG
        sources.append(f"- **{src}**{page_str}")

    # 4) Nếu không có dữ liệu thì báo không có
    if not contexts:
        return "Không có thông tin.", []

    # 5) Gọi LLM tổng hợp kèm guideline ngắn + ngữ cảnh
    sys = (
        "Bạn là trợ lý kỹ thuật Vertiv. Chỉ dùng đúng thông tin trong ngữ cảnh; "
        "nếu không thấy, trả lời “Không có thông tin.”"
    )
    prompt = (
        f"[Ngữ cảnh]\n{'\n---\n'.join(contexts)}\n\n"
        f"[Câu hỏi] {query}\n"
        f"[Yêu cầu] Trả lời ngắn gọn, có gạch đầu dòng nếu là thông số."
    )
    chat = oa.chat.completions.create(
        model=GEN_MODEL,
        messages=[{"role": "system", "content": sys},
                  {"role": "user", "content": prompt}],
        temperature=0.2,
    )
    reply = chat.choices[0].message.content.strip()
    if not reply or reply.lower().startswith("không có"):
        return "Không có thông tin.", []
    return reply, sources[:3]  # trả tối đa 3 nguồn