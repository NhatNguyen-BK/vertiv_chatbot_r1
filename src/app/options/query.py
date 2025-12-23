# src/app/options/query.py
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, QueryRequest
from openai import OpenAI
import os
from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel
import json

# LlamaIndex imports
from llama_index.core import VectorStoreIndex, QueryBundle, Settings, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.postprocessor import LLMRerank
from llama_index.core.vector_stores.types import (
    VectorStoreQueryMode,
    MetadataFilters,
    MetadataFilter,
    FilterOperator,
)
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import NodeWithScore
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from typing import List, Any

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
# collections = client.get_collections() # Optional check

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

# Wrapper cho LlamaIndex Embedding
class BGEM3LlamaIndexEmbedding(BaseEmbedding):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _get_query_embedding(self, query: str) -> List[float]:
        return _embed(query)
    
    def _get_text_embedding(self, text: str) -> List[float]:
        return _embed(text)
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

# Setup Settings globally (optional but good practice)
Settings.embed_model = BGEM3LlamaIndexEmbedding()
# Use existing OpenAI key for LlamaIndex LLM
Settings.llm = LlamaOpenAI(model=GEN_MODEL, api_key=os.getenv("OPENAI_API_KEY"))

def answer(query: str, file_names: list[str] | None = None, use_google_fallback: bool = False, force_google_search: bool = False, retrieval_config: dict | None = None, conversation_history: list[dict] | None = None):
    
    # Nếu bắt buộc search Google (từ frontend fallback flow)
    if force_google_search:
        print("🚀 Force Google Search requested")
        fallback_response, fallback_sources, fallback_chunks = _google_fallback_answer(query, conversation_history)
        # Thêm thông báo
        if fallback_response and not fallback_response.startswith("Không có thông tin"):
             notice = "⚠️ **Không tìm thấy trong tài liệu nội bộ. Đang sử dụng Google Search để tìm kiếm thông tin...**\n\n---\n\n"
             fallback_response = notice + fallback_response
        return fallback_response, fallback_sources, fallback_chunks

    # ===== BƯỚC 1: Routing - kiểm tra loại câu hỏi =====

    route_result = route_query(query, conversation_history)
    
    # Nếu là small talk, catalog query, hoặc google search (thủ công), trả về ngay
    if route_result["tool"] in ["small_talk", "catalog", "google_search"]:
        response = route_result["response"]
        sources = route_result.get("sources", [])
        # Với Google search, trả về results nếu có
        chunks_data = []
        if route_result["tool"] == "google_search":
            # Format lại results thành chunks_data để hiển thị trên frontend
            for result in route_result.get("results", []):
                chunks_data.append({
                    "text": result.get("snippet", ""),
                    "source": result.get("link", ""),
                    "page_range": [],
                    "score": None,
                    "title": result.get("title", "")
                })
        return response, sources, chunks_data
    
    # ===== BƯỚC 2: RAG - tìm kiếm trong Qdrant =====
    rag_response, rag_sources, rag_chunks = _rag_answer(query, file_names, retrieval_config, conversation_history)

    
    # ===== BƯỚC 3: Google Fallback - nếu RAG không có kết quả và toggle bật =====
    if use_google_fallback and (not rag_response or rag_response.lower().startswith("không có thông tin")):
        print("🔍 RAG không có kết quả, đang fallback sang Google Search...")
        fallback_response, fallback_sources, fallback_chunks = _google_fallback_answer(query, conversation_history)
        
        # Thêm thông báo đầu response để user biết đang dùng Google
        if fallback_response and not fallback_response.startswith("Không có thông tin"):
            notice = "⚠️ **Không tìm thấy trong tài liệu nội bộ. Đang sử dụng Google Search để tìm kiếm thông tin...**\n\n---\n\n"
            fallback_response = notice + fallback_response
        
        return fallback_response, fallback_sources, fallback_chunks
    
    return rag_response, rag_sources, rag_chunks


def _google_fallback_answer(query: str, conversation_history: list[dict] | None = None):
    """
    Tìm kiếm Google và xử lý kết quả giống như RAG:
    1. Lấy Google search results
    2. Dùng snippets làm contexts
    3. Đưa vào LLM để tổng hợp như RAG
    """
    from .tools import handle_google_search
    
    google_result = handle_google_search(query, num_results=5, conversation_history=conversation_history)
    
    print(f"📦 Google result keys: {list(google_result.keys())}")
    print(f"📝 Response length: {len(google_result.get('response', ''))}")
    print(f"📊 Results count: {len(google_result.get('results', []))}")
    
    # Nếu Google search thất bại
    if not google_result["response"] or google_result["response"].startswith("❌"):
        print("❌ Google search failed or no response")
        return "Không có thông tin.", [], []
    
    # Lấy results để làm contexts
    results = google_result.get("results", [])
    if not results:
        print("⚠️ No results in google_result")
        return "Không có thông tin.", [], []
    
    print(f"✅ Processing {len(results)} Google results for LLM")
    
    # 1) Tạo contexts từ Google snippets và content
    contexts = []
    sources = []
    chunks_data = []
    
    for idx, result in enumerate(results, 1):
        title = result.get("title", "")
        link = result.get("link", "")
        snippet = result.get("snippet", "")
        content = result.get("content", "")  # Nếu có scrape content
        
        # Dùng content nếu có, không thì dùng snippet
        context_text = content if content and not content.startswith("❌") else snippet
        
        if context_text:
            contexts.append(context_text)
            sources.append(f"- [{title}]({link})")
            chunks_data.append({
                "text": context_text,
                "source": link,
                "page_range": [],
                "score": None,
                "title": title,
                "from_google": True
            })
    
    if not contexts:
        print("⚠️ No contexts created from results")
        return "Không có thông tin.", [], []
    
    print(f"📝 Created {len(contexts)} contexts for LLM (total chars: {sum(len(c) for c in contexts)})")
    
    # 2) Đưa vào LLM để tổng hợp giống như RAG
    numbered_contexts = []
    for idx, ctx in enumerate(contexts, 1):
        numbered_contexts.append(f"[Nguồn {idx}]\n{ctx}")
    
    sys = (
        "Bạn là trợ lý thông minh. Dựa trên thông tin tìm kiếm từ Internet, trả lời câu hỏi một cách NGẮN GỌN và ĐÚNG TRỌNG TÂM.\n\n"
        "QUY TẮC QUAN TRỌNG:\n"
        "1. Trả lời trực tiếp vào câu hỏi, KHÔNG dài dòng văn tự\n"
        "3. Sử dụng gạch đầu dòng để trình bày rõ ràng\n"
        "4. Trích dẫn chính xác các đoạn văn bản quan trọng\n\n"
        "Trả về JSON với format:\n"
        "{\n"
        '  "answer": "câu trả lời ngắn gọn của bạn",\n'
        '  "citations": [\n'
        '    {"quote": "đoạn trích dẫn chính xác", "context_index": 1}\n'
        '  ]\n'
        "}\n"
        "Nếu không có thông tin, trả về answer là 'Không có thông tin.' và citations rỗng."
    )
    
    # Xử lý conversation_history - giới hạn 10 tin nhắn gần nhất
    messages = [{"role": "system", "content": sys}]
    
    # Không dùng history để đảm bảo ngắn gọn
    # if conversation_history:
    #     # Lấy 10 tin nhắn gần nhất
    #     recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    #     messages.extend(recent_history)
    pass
    
    prompt = (
        f"[Thông tin từ Internet]\n{chr(10).join(numbered_contexts)}\n\n"
        f"[Câu hỏi] {query}\n\n"
        f"[Yêu cầu] Hãy trả lời NGẮN GỌN và SÚC TÍCH dựa trên thông tin trên:\n"
        f"- Sử dụng gạch đầu dòng để trình bày rõ ràng nếu cần\n"
        f"- Trích dẫn chính xác các đoạn văn bản quan trọng (giới hạn mỗi quote trong 150 ký tự)"
    )
    
    messages.append({"role": "user", "content": prompt})
    
    try:
        print("🤖 Calling LLM to synthesize Google results...")
        chat = oa.chat.completions.create(
            model=GEN_MODEL,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        print(f"✅ LLM response received")
        result = json.loads(chat.choices[0].message.content)
        reply = result.get("answer", "").strip()
        citations = result.get("citations", [])
        
        print(f"💬 Reply length: {len(reply)}, Citations count: {len(citations)}")
        print(f"📝 Reply preview: {reply[:100]}...")
        
        if not reply or reply.lower().startswith("không có"):
            print("⚠️ LLM returned 'no info'")
            return "Không có thông tin.", [], chunks_data
        
        # Tạo sources từ citations
        final_sources = []
        for citation in citations:
            ctx_idx = citation.get("context_index", 1) - 1  # convert to 0-based
            quote = citation.get("quote", "")
            
            if 0 <= ctx_idx < len(results):
                result_item = results[ctx_idx]
                title = result_item.get("title", "")
                link = result_item.get("link", "")
                
                final_sources.append(f"- [{title}]({link})\n  > *\"{quote}\"*")
        
        # Nếu không có citations, fallback về sources gốc
        if not final_sources:
            final_sources = sources[:3]
        
        # Thêm note rằng thông tin từ Google và nguồn tham khảo
        sources_text = "\n".join(final_sources)
        reply_with_note = f"{reply}\n\n---\n**Nguồn tham khảo:**\n{sources_text}\n\n*ℹ️ Thông tin được tổng hợp từ kết quả tìm kiếm trên Internet*"
        
        print(f"✅ Returning Google fallback answer: {len(reply_with_note)} chars, {len(final_sources)} sources, {len(chunks_data)} chunks")
        
        return reply_with_note, final_sources[:3], chunks_data
        
    except Exception as e:
        print(f"❌ Error processing Google results with LLM: {e}")
        import traceback
        print(traceback.format_exc())
        # Fallback: trả về snippet đầu tiên
        if contexts:
            print(f"🔄 Fallback: returning first context")
            return contexts[0], sources[:1], chunks_data
        return "Không có thông tin.", [], []


def _rag_answer(query: str, file_names: list[str] | None = None, retrieval_config: dict | None = None, conversation_history: list[dict] | None = None):
    # Default config
    # initial_top_k acts as similarity_top_k (dense)
    similarity_top_k = 10
    sparse_top_k = 10
    hybrid_top_k = 10
    vector_store_query_mode = "hybrid"
    alpha = 0.5
    rerank_top_k = 5
    score_threshold = None 

    if retrieval_config:
        similarity_top_k = retrieval_config.get("initial_top_k", similarity_top_k)
        sparse_top_k = retrieval_config.get("sparse_top_k", sparse_top_k)
        hybrid_top_k = retrieval_config.get("hybrid_top_k", hybrid_top_k)
        vector_store_query_mode = retrieval_config.get("vector_store_query_mode", vector_store_query_mode)
        alpha = retrieval_config.get("alpha", alpha)
        rerank_top_k = retrieval_config.get("rerank_top_k", rerank_top_k)
        score_threshold = retrieval_config.get("score_threshold", score_threshold)

    print(f"✅ Connected to Qdrant. Using collection: {QDRANT_COLLECTION}")
    print(f"🔍 Parameters: sim_k={similarity_top_k}, sparse_k={sparse_top_k}, hybrid_k={hybrid_top_k}, mode={vector_store_query_mode}, alpha={alpha}")

    # ===== REFRACTION: LlamaIndex Retreival =====
    
    # 1. Setup Vector Store
    # NOTE: Assuming 'dense' and 'sparse' vector names from original code logic.
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION,
        enable_hybrid=True, # Enable Hybrid search
        batch_size=15,
    )
    
    # 2. Setup Index
    # We use our custom embeddings wrapper
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=BGEM3LlamaIndexEmbedding()
    )
    
    # 3. Build Filters
    filters_chunk = None
    if file_names and len(file_names) > 0:
        filters_chunk = MetadataFilters(
            filters=[
                MetadataFilter(key="source", operator=FilterOperator.IN, value=file_names),
            ]
        )
    
    # Map string mode to Enum
    try:
        vs_mode = VectorStoreQueryMode(vector_store_query_mode)
    except ValueError:
        print(f"⚠️ Invalid query mode '{vector_store_query_mode}', defaulting to HYBRID")
        vs_mode = VectorStoreQueryMode.HYBRID

    # 4. Create Retriever
    retriever = index.as_retriever(
        similarity_top_k=similarity_top_k, 
        sparse_top_k=sparse_top_k, 
        vector_store_query_mode=vs_mode,
        filters=filters_chunk,
        alpha=alpha,
        hybrid_top_k=hybrid_top_k
    )
    
    # 5. Retrieve Nodes
    # NOTE: LlamaIndex will generate embeddings using our embed_model
    # For hybrid, it expects the vector store to handle sparse generation or provided vector.
    # Since we didn't explicitly pass a sparse function to QdrantVectorStore, 
    # if it fails we might need to adjust. But we'll try standard flow first.
    print(f"🔍 Retrieving nodes for query: {query}")
    try:
        retrieved_nodes = retriever.retrieve(query)
    except Exception as e:
        print(f"⚠️ Error in retrieval: {e}")
        # Fallback to pure dense if hybrid fails?
        # Or return empty
        return "Có lỗi xảy ra khi truy vấn dữ liệu.", [], []

    print(f"✅ Retrieved {len(retrieved_nodes)} nodes from Qdrant")

    # 6. Rerank using LLM
    if retrieved_nodes:
        # Define custom Vietnamese rerank prompt to match original logic
        rerank_prompt_str = """
Một danh sách các tài liệu (các đoạn văn bản) được cung cấp bên dưới.
Mỗi tài liệu có một số thứ tự bên cạnh. Một câu hỏi cũng được cung cấp.

Nhiệm vụ:
- Xếp hạng các tài liệu dựa trên mức độ hữu ích của chúng để trả lời câu hỏi.
- Gán điểm độ liên quan từ 1 đến 10 cho mỗi tài liệu (10 = rất liên quan, 1 = ít liên quan).
- Loại bỏ các tài liệu không liên quan.
- Chỉ trả về danh sách đã xếp hạng theo thứ tự giảm dần của độ liên quan.

Định dạng mẫu:
Tài liệu 1:
<nội dung tài liệu 1>

Tài liệu 2:
<nội dung tài liệu 2>

...

Câu hỏi: <câu hỏi của người dùng>

Câu trả lời:
Doc: 2, Relevance: 9
Doc: 5, Relevance: 7
Doc: 3, Relevance: 4

---

Bây giờ hãy thử với dữ liệu sau:

{context_str}
Câu hỏi: {query_str}
Câu trả lời:
"""
        from llama_index.core.prompts import PromptTemplate, PromptType
        custom_rerank_prompt = PromptTemplate(
            rerank_prompt_str, prompt_type=PromptType.CHOICE_SELECT
        )

        reranker = LLMRerank(
            choice_batch_size=5,
            top_n=rerank_top_k,
            llm=Settings.llm,
            choice_select_prompt=custom_rerank_prompt
        )
        
        print("🔄 Reranking nodes...")
        try:
            reranked_nodes = reranker.postprocess_nodes(
                retrieved_nodes, query_bundle=QueryBundle(query)
            )
        except Exception as e:
            print(f"⚠️ Error in reranking: {e}")
            reranked_nodes = retrieved_nodes[:rerank_top_k]
    else:
        reranked_nodes = []
    
    print(f"✅ Post-rerank count: {len(reranked_nodes)}")

    # 7. Convert nodes to internal format
    contexts = []
    sources = []  # list[str] để hiển thị
    chunks_data = []  # Lưu thông tin chunks để trả về frontend

    for node in reranked_nodes:
        # node is NodeWithScore
        # Metadata is in node.metadata
        # Text is node.text (or node.get_content())
        meta = node.metadata
        
        src = meta.get("source", "unknown.pdf")
        pages = meta.get("page_range")
        page_str = ""
        if isinstance(pages, list) and pages:
            page_str = f" (trang {pages[0]})"
        
        # Existing logic used 'source_text' from payload directly if available. 
        # LlamaIndex usually puts payload into metadata.
        # But 'text' field of Node should be the chunk text.
        source_text = node.get_content()
        
        contexts.append(source_text)
        sources.append(f"- **{src}**{page_str}")
        
        chunks_data.append({
            "text": source_text,
            "source": src,
            "page_range": pages if isinstance(pages, list) else [],
            "score": node.score
        })
    
    # 8. Nếu không có dữ liệu thì báo không có
    if not contexts:
        return "Không có thông tin.", [], []

    # 9. Gọi LLM tổng hợp (reuse existing prompt logic)
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
    
    messages = [{"role": "system", "content": sys}]
    
    prompt = (
        f"[Ngữ cảnh]\n{chr(10).join(numbered_contexts)}\n\n"
        f"[Câu hỏi] {query}\n"
        f"[Yêu cầu] Trả lời ngắn gọn, có gạch đầu dòng nếu là thông số. "
        f"Trích dẫn chính xác các đoạn văn bản từ ngữ cảnh mà bạn sử dụng (giới hạn mỗi quote trong 150 ký tự)."
    )
    
    messages.append({"role": "user", "content": prompt})
    chat = oa.chat.completions.create(
        model=GEN_MODEL,
        messages=messages,
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
            
            if 0 <= ctx_idx < len(reranked_nodes):
                # Retrieve metadata again from correct node
                node = reranked_nodes[ctx_idx]
                meta = node.metadata
                src = meta.get("source", "unknown.pdf")
                pages = meta.get("page_range")
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