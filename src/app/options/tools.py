# src/app/options/tools.py
"""
Các tool hỗ trợ cho chatbot:
- Small talk: xử lý chào hỏi, cảm ơn
- Product catalog: liệt kê sản phẩm
"""
from typing import Dict, List, Tuple
import re

# Danh sách sản phẩm hiện có
PRODUCTS = {
    "DC_Power": [
        {"name": "Netsure 210", "desc": "Hệ thống nguồn DC"},
        {"name": "Netsure 531", "desc": "Hệ thống nguồn DC"},
        {"name": "Netsure 731", "desc": "Hệ thống nguồn DC"},
    ],
    "Thermal": [
        {"name": "Liebert Crv", "desc": "Hệ thống làm mát phòng"},
        {"name": "Libert Pex3", "desc": "Hệ thống làm mát chính xác"},
        {"name": "Libert Pex4", "desc": "Hệ thống làm mát chính xác"},
    ],
    "UPS": [
        {"name": "Liebert Apm", "desc": "Hệ thống UPS"},
        {"name": "Liebert Exs", "desc": "Hệ thống UPS"},
        {"name": "Liebrt Mtp", "desc": "Hệ thống UPS"},
    ],
}

# Pattern cho small talk
SMALL_TALK_PATTERNS = [
    r"^(xin chào|chào|hello|hi|hey)\b",
    r"^(cảm ơn|thanks|thank you|cám ơn)\b",
    r"^(tạm biệt|bye|goodbye)\b",
    r"^(bạn là ai|bạn tên gì|who are you)\b",
    r"^(bạn có thể giúp|bạn giúp|help)\b",
]

# Pattern cho product catalog
CATALOG_PATTERNS = [
    r"(có bao nhiêu|có mấy|danh sách|list).*(sản phẩm|product)",
    r"(sản phẩm|product).*(nào|gì|what)",
    r"(liệt kê|cho biết|cho tôi).*(sản phẩm|product)",
    r"^(sản phẩm|product)",
]


def is_small_talk(query: str) -> bool:
    """Kiểm tra xem câu hỏi có phải small talk không"""
    query_lower = query.lower().strip()
    return any(re.search(pattern, query_lower) for pattern in SMALL_TALK_PATTERNS)


def is_catalog_query(query: str) -> bool:
    """Kiểm tra xem câu hỏi có phải về danh sách sản phẩm không"""
    query_lower = query.lower().strip()
    return any(re.search(pattern, query_lower) for pattern in CATALOG_PATTERNS)


def handle_small_talk(query: str) -> str:
    """Xử lý các câu hỏi chào hỏi, cảm ơn"""
    query_lower = query.lower().strip()
    
    if re.search(r"^(xin chào|chào|hello|hi|hey)\b", query_lower):
        return (
            "Xin chào! 👋\n\n"
            "Tôi là trợ lý ảo của Vertiv, chuyên hỗ trợ thông tin về các sản phẩm:\n"
            "- **DC Power**: Netsure 210, 531, 731\n"
            "- **Thermal**: Liebert CRV, PEX3, PEX4\n"
            "- **UPS**: Liebert APM, EXS, MTP\n\n"
            "Bạn có thể hỏi tôi về thông số kỹ thuật, tính năng, hoặc bất kỳ thông tin nào về các sản phẩm này."
        )
    
    if re.search(r"^(cảm ơn|thanks|thank you|cám ơn)\b", query_lower):
        return (
            "Rất vui được giúp đỡ bạn! 😊\n\n"
            "Nếu còn câu hỏi nào về sản phẩm Vertiv, đừng ngại hỏi nhé!"
        )
    
    if re.search(r"^(tạm biệt|bye|goodbye)\b", query_lower):
        return "Tạm biệt! Chúc bạn một ngày tốt lành! 👋"
    
    if re.search(r"^(bạn là ai|bạn tên gì|who are you)\b", query_lower):
        return (
            "Tôi là **Vertiv Assistant** - trợ lý ảo chuyên về sản phẩm Vertiv.\n\n"
            "Tôi được huấn luyện với kiến thức về:\n"
            "- Hệ thống nguồn DC (DC Power)\n"
            "- Hệ thống làm mát (Thermal)\n"
            "- Hệ thống UPS\n\n"
            "Hãy hỏi tôi bất kỳ điều gì về các sản phẩm này!"
        )
    
    if re.search(r"^(bạn có thể giúp|bạn giúp|help)\b", query_lower):
        return (
            "Tất nhiên! Tôi có thể giúp bạn:\n\n"
            "✅ Tra cứu thông số kỹ thuật sản phẩm\n"
            "✅ So sánh các model khác nhau\n"
            "✅ Tìm hiểu tính năng và ứng dụng\n"
            "✅ Giải đáp thắc mắc về sản phẩm Vertiv\n\n"
            "Bạn muốn biết thông tin gì?"
        )
    
    return None


def handle_catalog_query(query: str) -> Tuple[str, List[str]]:
    """Trả về danh sách sản phẩm"""
    # Tính tổng số sản phẩm
    total = sum(len(products) for products in PRODUCTS.values())
    
    response = f"**Vertiv hiện có {total} dòng sản phẩm chính:**\n\n"
    
    # DC Power
    response += "### 🔋 DC Power (Hệ thống nguồn DC)\n"
    for p in PRODUCTS["DC_Power"]:
        response += f"- **{p['name']}**: {p['desc']}\n"
    
    response += "\n### ❄️ Thermal (Hệ thống làm mát)\n"
    for p in PRODUCTS["Thermal"]:
        response += f"- **{p['name']}**: {p['desc']}\n"
    
    response += "\n### ⚡ UPS (Bộ lưu điện)\n"
    for p in PRODUCTS["UPS"]:
        response += f"- **{p['name']}**: {p['desc']}\n"
    
    response += "\n\n💡 *Bạn có thể chọn sản phẩm cụ thể ở dropdown bên trên để tìm hiểu chi tiết!*"
    
    # Nguồn giả (vì không cần search)
    sources = ["- **Danh mục sản phẩm Vertiv**"]
    
    return response, sources


def route_query(query: str) -> Dict:
    """
    Phân loại câu hỏi và trả về loại tool cần dùng
    Returns:
        {
            "tool": "small_talk" | "catalog" | "rag",
            "response": str (nếu đã có sẵn) | None
        }
    """
    if is_small_talk(query):
        return {
            "tool": "small_talk",
            "response": handle_small_talk(query)
        }
    
    if is_catalog_query(query):
        response, sources = handle_catalog_query(query)
        return {
            "tool": "catalog",
            "response": response,
            "sources": sources
        }
    
    # Mặc định dùng RAG
    return {
        "tool": "rag",
        "response": None
    }
