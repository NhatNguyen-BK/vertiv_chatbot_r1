# src/app/query.py
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, QueryRequest
from openai import OpenAI
import os
from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel
import json
load_dotenv()

# Import tools mới
from .tools import route_query

oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
BGE_M3_MODEL = os.getenv("BGE_M3_MODEL", "BAAI/bge-m3")
GEN_MODEL   = os.getenv("GEN_MODEL", "gpt-4o-mini")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "vertiv_docs1")

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
collections = client.get_collections()

# Khởi tạo BGE-M3 model
print("🔄 Loading BGE-M3 model for query...")
bge_m3_model = BGEM3FlagModel(BGE_M3_MODEL, use_fp16=True)
print("✅ BGE-M3 model loaded successfully!")

def _embed(text: str):
    """Tạo dense vector từ BGE-M3"""
    embeddings = bge_m3_model.encode(
        [text], 
        return_dense=True, 
        return_sparse=False,
        return_colbert_vecs=False
    )
    return embeddings['dense_vecs'][0].tolist()

def _embed_sparse(text: str):
    """Tạo sparse vector từ BGE-M3"""
    embeddings = bge_m3_model.encode(
        [text], 
        return_dense=False, 
        return_sparse=True,
        return_colbert_vecs=False
    )
    weights = embeddings['lexical_weights'][0]
    return {
        "indices": [int(idx) for idx in weights.keys()],
        "values": [float(val) for val in weights.values()]
    }

def _llm_rerank(query: str, hits: list, top_k: int = 5):
    """
    Sử dụng LLM (OpenAI) để đánh giá lại độ liên quan của các chunks
    
    Args:
        query: Câu hỏi của người dùng
        hits: List các ScoredPoint từ Qdrant
        top_k: Số lượng kết quả trả về (mặc định 5)
    
    Returns:
        List các chunks đã được rerank theo thứ tự relevance
    """
    if len(hits) <= top_k:
        return hits
    
    # Chuẩn bị prompt cho LLM
    chunks_text = []
    for idx, hit in enumerate(hits):
        payload = hit.payload or {}
        text = payload.get("source_text", "")[:500]  # Giới hạn 500 ký tự
        chunks_text.append(f"[{idx}] {text}")
    
    prompt = f"""Cho câu hỏi: "{query}"

Đánh giá độ liên quan của các đoạn văn sau (0-10 điểm):

{chr(10).join(chunks_text)}

Trả về JSON array với format: [{{"index": 0, "score": 9}}, {{"index": 1, "score": 7}}, ...]
Chỉ trả về top {top_k} kết quả có điểm cao nhất, sắp xếp giảm dần."""

    try:
        response = oa.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia đánh giá độ liên quan của văn bản. Chỉ trả về JSON, không giải thích."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        
        result = json.loads(response.choices[0].message.content)
        print("Rerank result:", result)
        
        # Xử lý kết quả trả về
        if isinstance(result, dict) and "results" in result:
            rankings = result["results"]
        elif isinstance(result, list):
            rankings = result
        else:
            # Fallback nếu format không đúng
            return hits[:top_k]
        
        # Sắp xếp lại hits theo rankings
        reranked = []
        for item in rankings[:top_k]:
            idx = item.get("index", -1)
            if 0 <= idx < len(hits):
                reranked.append(hits[idx])
        
        # Nếu không đủ top_k, thêm các chunks còn lại
        if len(reranked) < top_k:
            used_indices = {item.get("index") for item in rankings}
            for idx, hit in enumerate(hits):
                if idx not in used_indices and len(reranked) < top_k:
                    reranked.append(hit)
        
        return reranked[:top_k]
    
    except Exception as e:
        print(f"LLM rerank error: {e}")
        # Fallback về kết quả gốc nếu có lỗi
        return hits[:top_k]

def answer(query: str, file_names: list[str] | None = None):
    # ===== BƯỚC 1: Routing - kiểm tra loại câu hỏi =====
    route_result = route_query(query)
    
    # Nếu là small talk hoặc catalog query, trả về ngay
    if route_result["tool"] in ["small_talk", "catalog"]:
        response = route_result["response"]
        sources = route_result.get("sources", [])
        return response, sources, []  # Không có chunks cho small talk
    
    # ===== BƯỚC 2: RAG - tìm kiếm trong Qdrant =====
    return _rag_answer(query, file_names)

def _rag_answer(query: str, file_names: list[str] | None = None):
    # 1) Lấy vector câu hỏi (dense và sparse)
    collections = client.get_collections()
    print(f"✅ Connected to Qdrant. Collections: {[c.name for c in collections.collections]}")
    dense_vec = _embed(query)
    sparse_vec = _embed_sparse(query)
    print("Collection: ", QDRANT_COLLECTION)
    # 2) Hybrid search trong Qdrant (kết hợp dense + sparse)
    # Sử dụng prefetch để tìm riêng rồi kết hợp
    search_params = {
        "collection_name": QDRANT_COLLECTION,
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
        "limit": 10,
    }
    
    # Thêm filter nếu có file_names (filter theo source field trong metadata)
    if file_names and len(file_names) > 0:
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="source",  # Filter theo source trong metadata
                    match=MatchAny(any=file_names)
                )
            ]
        )
        # Thêm filter vào cả prefetch
        search_params["prefetch"][0].filter = query_filter
        search_params["prefetch"][1].filter = query_filter
        search_params["query_filter"] = query_filter
    
    hits = client.query_points(**search_params).points
    print("sssssssssssssss: ", hits)
    
    # 3) LLM Reranking - Sử dụng OpenAI để đánh giá lại 10 kết quả
    if len(hits) > 5:
        reranked_hits = _llm_rerank(query, hits, top_k=5)
    else:
        reranked_hits = hits
    
    # 4) Gom ngữ cảnh & nguồn từ kết quả đã rerank
    contexts = []
    sources = []  # list[str] để hiển thị
    chunks_data = []  # Lưu thông tin chunks để trả về frontend
    
    for h in reranked_hits:
        p = h.payload or {}
        meta = p.get("metadata", {})  # nếu lúc upsert bạn gộp metadata vào payload
        # tùy vào cách bạn lưu, thử theo 2 key phổ biến:
        src = meta.get("source") or p.get("source") or "unknown.pdf"
        pages = meta.get("page_range") or p.get("page_range")
        page_str = ""
        if isinstance(pages, list) and pages:
            page_str = f" (trang {pages[0]})"
        
        source_text = p.get("source_text", "")
        contexts.append(source_text)  # phần text gốc để làm RAG
        sources.append(f"- **{src}**{page_str}")
        
        # Thêm thông tin chunk để trả về frontend
        chunks_data.append({
            "text": source_text,
            "source": src,
            "page_range": pages if isinstance(pages, list) else [],
            "score": h.score if hasattr(h, 'score') else None
        })

    # 4) Nếu không có dữ liệu thì báo không có
    if not contexts:
        return "Không có thông tin.", [], []

    # 5) Gọi LLM tổng hợp kèm guideline ngắn + ngữ cảnh
    # Đánh số các đoạn ngữ cảnh
    numbered_contexts = []
    for idx, ctx in enumerate(contexts, 1):
        numbered_contexts.append(f"[Đoạn {idx}]\n{ctx}")
    
    sys = (
        "Bạn là trợ lý kỹ thuật Vertiv. Chỉ dùng đúng thông tin trong ngữ cảnh được cung cấp.\n"
        "Khi trả lời, bạn PHẢI trích dẫn chính xác đoạn văn bản từ ngữ cảnh mà bạn sử dụng.\n"
        "Trả về JSON với format:\n"
        "{\n"
        '  "answer": "câu trả lời của bạn",\n'
        '  "citations": [\n'
        '    {"quote": "đoạn trích dẫn chính xác", "context_index": 1}\n'
        '  ]\n'
        "}\n"
        "Nếu không có thông tin, trả về answer là 'Không có thông tin.' và citations rỗng."
    )
    prompt = (
        f"[Ngữ cảnh]\n{chr(10).join(numbered_contexts)}\n\n"
        f"[Câu hỏi] {query}\n"
        f"[Yêu cầu] Trả lời ngắn gọn, có gạch đầu dòng nếu là thông số. "
        f"Trích dẫn chính xác các đoạn văn bản từ ngữ cảnh mà bạn sử dụng (giới hạn mỗi quote trong 150 ký tự)."
    )
    chat = oa.chat.completions.create(
        model=GEN_MODEL,
        messages=[{"role": "system", "content": sys},
                  {"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(chat.choices[0].message.content)
        reply = result.get("answer", "").strip()
        citations = result.get("citations", [])
        
        if not reply or reply.lower().startswith("không có"):
            return "Không có thông tin.", [], chunks_data
        
        # Tạo sources từ citations
        final_sources = []
        for citation in citations:
            ctx_idx = citation.get("context_index", 1) - 1  # convert to 0-based
            quote = citation.get("quote", "")
            
            if 0 <= ctx_idx < len(reranked_hits):
                h = reranked_hits[ctx_idx]
                p = h.payload or {}
                meta = p.get("metadata", {})
                src = meta.get("source") or p.get("source") or "unknown.pdf"
                pages = meta.get("page_range") or p.get("page_range")
                page_str = ""
                if isinstance(pages, list) and pages:
                    page_str = f" (trang {pages[0]})"
                
                final_sources.append(f"- **{src}**{page_str}\n  > *\"{quote}\"*")
        
        # Nếu không có citations, fallback về sources cũ
        if not final_sources:
            final_sources = sources[:3]
        
        return reply, final_sources[:3], chunks_data
    
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        # Fallback về cách cũ nếu có lỗi
        reply = chat.choices[0].message.content.strip()
        if not reply or reply.lower().startswith("không có"):
            return "Không có thông tin.", [], chunks_data
        return reply, sources[:3], chunks_data