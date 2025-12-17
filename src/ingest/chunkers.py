# src/ingest/chunkers.py
import re
from typing import List, Dict
from .schema import DocMeta
from .parser import parse_any

# Tham số chunk size cho BGE-M3
MIN_CHUNK_CHARS = 70      # Chunks nhỏ hơn 70 ký tự sẽ được merge
MAX_CHUNK_CHARS = 1024    # Chunks lớn hơn 1024 ký tự sẽ được split

def extract_header(text: str) -> str:
    """
    Trích xuất header từ chunk text.
    Header thường là dòng đầu tiên hoặc các dòng bắt đầu với # (markdown)
    hoặc các dòng viết HOA hoàn toàn.
    """
    lines = text.strip().split('\n')
    headers = []
    
    for line in lines[:5]:  # Chỉ xem 5 dòng đầu
        line = line.strip()
        if not line:
            continue
        # Markdown headers
        if line.startswith('#'):
            headers.append(line)
        # Dòng viết HOA (có thể là tiêu đề)
        elif line.isupper() and len(line) > 3:
            headers.append(line)
        # Dòng ngắn kết thúc bằng : (có thể là tiêu đề)
        elif line.endswith(':') and len(line) < 100:
            headers.append(line)
        else:
            # Dừng lại khi gặp nội dung thông thường
            break
    
    return '\n'.join(headers) if headers else ""

def split_large_chunk(text: str, max_chars: int, header: str = "") -> List[str]:
    """
    Tách chunk lớn thành các chunk nhỏ hơn, giữ header cho mỗi chunk con.
    """
    if len(text) <= max_chars:
        return [text]
    
    # Nếu có header, giảm max_chars để chừa chỗ cho header
    effective_max = max_chars
    if header:
        header_with_separator = header + "\n---\n"
        effective_max = max_chars - len(header_with_separator)
        if effective_max < 200:  # Đảm bảo có chỗ cho content
            effective_max = 200
    
    chunks = []
    
    # Thử split theo paragraph trước
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if len(current_chunk) + len(para) + 2 <= effective_max:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                # Thêm header vào chunk
                if header and current_chunk != header:
                    chunks.append(header + "\n---\n" + current_chunk)
                else:
                    chunks.append(current_chunk)
            
            # Nếu paragraph đơn lẻ quá dài, split theo câu
            if len(para) > effective_max:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= effective_max:
                        current_chunk = current_chunk + " " + sent if current_chunk else sent
                    else:
                        if current_chunk:
                            if header:
                                chunks.append(header + "\n---\n" + current_chunk)
                            else:
                                chunks.append(current_chunk)
                        # Nếu câu đơn quá dài, cắt cứng
                        if len(sent) > effective_max:
                            for i in range(0, len(sent), effective_max):
                                sub = sent[i:i+effective_max]
                                if header:
                                    chunks.append(header + "\n---\n" + sub)
                                else:
                                    chunks.append(sub)
                            current_chunk = ""
                        else:
                            current_chunk = sent
            else:
                current_chunk = para
    
    # Thêm chunk cuối cùng
    if current_chunk:
        if header and current_chunk != header:
            chunks.append(header + "\n---\n" + current_chunk)
        else:
            chunks.append(current_chunk)
    
    return chunks if chunks else [text[:max_chars]]

def merge_small_chunks(chunks: List[Dict], min_chars: int) -> List[Dict]:
    """
    Merge các chunks nhỏ hơn min_chars vào chunk tiếp theo.
    Giữ metadata của chunk được merge vào.
    """
    if not chunks:
        return []
    
    merged = []
    carry_text = ""
    carry_meta = None
    
    for chunk in chunks:
        text = chunk["text"]
        
        if carry_text:
            # Gộp carry vào chunk hiện tại
            text = carry_text + "\n\n" + text
            carry_text = ""
            carry_meta = None
        
        if len(text) < min_chars:
            # Chunk quá nhỏ, carry sang chunk tiếp theo
            carry_text = text
            carry_meta = chunk["metadata"]
        else:
            # Chunk đủ lớn, thêm vào kết quả
            chunk["text"] = text
            merged.append(chunk)
    
    # Xử lý carry cuối cùng
    if carry_text:
        if merged:
            # Gộp vào chunk cuối
            merged[-1]["text"] = merged[-1]["text"] + "\n\n" + carry_text
        else:
            # Không có chunk nào, giữ lại carry
            merged.append({"text": carry_text, "metadata": carry_meta})
    
    return merged

def process_chunks_for_bge_m3(chunks: List[Dict], min_chars: int = MIN_CHUNK_CHARS, max_chars: int = MAX_CHUNK_CHARS) -> List[Dict]:
    """
    Xử lý chunks để phù hợp với BGE-M3:
    1. Merge chunks < min_chars vào chunk tiếp theo
    2. Split chunks > max_chars, giữ header
    """
    if not chunks:
        return []
    
    # Bước 1: Merge chunks nhỏ
    merged_chunks = merge_small_chunks(chunks, min_chars)
    
    # Bước 2: Split chunks lớn
    final_chunks = []
    for chunk in merged_chunks:
        text = chunk["text"]
        
        if len(text) > max_chars:
            # Trích xuất header
            header = extract_header(text)
            
            # Split chunk
            sub_texts = split_large_chunk(text, max_chars, header)
            
            for i, sub_text in enumerate(sub_texts):
                # Clone metadata
                new_meta = chunk["metadata"].copy()
                # Cập nhật page_range nếu cần (thêm suffix cho sub-chunks)
                if isinstance(new_meta.get("page_range"), list) and new_meta["page_range"]:
                    # Giữ nguyên page_range gốc
                    pass
                
                final_chunks.append({
                    "text": sub_text,
                    "metadata": new_meta
                })
        else:
            final_chunks.append(chunk)
    
    return final_chunks

def file_to_chunks(
    path: str,
    meta: DocMeta,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = 150
) -> List[Dict]:
    """
    Đọc file (PDF / Excel / CSV / Ảnh OCR) -> text (parser),
    sau đó chia text thành các chunk có overlap và gắn metadata.
    Xử lý thêm: merge chunks nhỏ, split chunks lớn cho BGE-M3.
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

    # Xử lý chunks cho BGE-M3
    processed_chunks = process_chunks_for_bge_m3(chunks, MIN_CHUNK_CHARS, max_chars)
    
    return processed_chunks

# Giữ alias cho tương thích ngược với code cũ
def pdf_to_chunks(path: str, meta: DocMeta, max_chars: int = MAX_CHUNK_CHARS, overlap: int = 150) -> List[Dict]:
    return file_to_chunks(path, meta, max_chars=max_chars, overlap=overlap)