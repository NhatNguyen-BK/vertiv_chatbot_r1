# src/app/options/tools.py
"""
Các tool hỗ trợ cho chatbot:
- Small talk: xử lý chào hỏi, cảm ơn
- Product catalog: liệt kê sản phẩm
"""
from typing import Dict, List, Tuple
import re
import os
import sys

# Import database modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.database.connect_db import SessionLocal
from src.database import crud


# ==================== DATABASE HELPER ====================
def get_products_from_db() -> Dict[str, List[Dict]]:
    """
    Lấy danh sách sản phẩm từ database
    Returns:
        {
            "DC Power": [{"name": "Netsure 210", "desc": "..."}],
            "Thermal": [...],
            ...
        }
    """
    db = SessionLocal()
    try:
        result = {}
        categories = crud.get_all_categories(db)
        
        for category in categories:
            product_lines = crud.get_product_lines_by_category(db, category.id)
            products_list = []
            
            for product_line in product_lines:
                products = crud.get_products_by_product_line(db, product_line.id)
                for product in products:
                    products_list.append({
                        "name": product_line.name,  # Tên product line
                        "desc": f"{category.name} - {product.name}"  # Mô tả
                    })
            
            if products_list:
                result[category.name] = products_list
        
        return result
    except Exception as e:
        print(f"⚠️  Error getting products from DB: {e}")
        # Fallback về danh sách mặc định nếu có lỗi
        return {
            "DC Power": [
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
    finally:
        db.close()

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
    """Trả về danh sách sản phẩm từ database"""
    # Lấy sản phẩm từ database
    PRODUCTS = get_products_from_db()
    
    # Tính tổng số sản phẩm
    total = sum(len(products) for products in PRODUCTS.values())
    
    response = f"**Vertiv hiện có {total} dòng sản phẩm chính:**\n\n"
    
    # Icon mapping
    icons = {
        "DC Power": "🔋",
        "Thermal": "❄️",
        "UPS": "⚡"
    }
    
    # Duyệt qua các category
    for category_name, products in PRODUCTS.items():
        icon = icons.get(category_name, "📦")
        response += f"### {icon} {category_name}\n"
        
        for p in products:
            response += f"- **{p['name']}**: {p['desc']}\n"
        
        response += "\n"
    
    response += "💡 *Bạn có thể chọn sản phẩm cụ thể ở dropdown bên trên để tìm hiểu chi tiết!*"
    
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
