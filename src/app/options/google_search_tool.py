# src/app/options/google_search_tool.py
"""
Google Search Tool - Tìm kiếm trên Google và scrape nội dung từ các trang web
Hỗ trợ chatbot tìm kiếm thông tin bên ngoài database
"""
import os
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import urllib3
from typing import List, Dict
from openai import OpenAI
import json

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# OpenAI client cho reformulation
oa = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- CẤU HÌNH ---
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "D:/Downloads/burnished-rider-480001-e0-fe4bb7f03c4f.json")
CSE_ID = os.getenv("GOOGLE_CSE_ID", "27228f3f7a7dc4fd3")
SCOPES = ['https://www.googleapis.com/auth/cse']

SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _get_credentials():
    """Lấy credentials từ service account"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return credentials
    except Exception as e:
        print(f"❌ Lỗi load credentials: {e}")
        return None


def reformulate_search_query(user_query: str, conversation_history: list[dict] | None = None) -> str:
    """
    Sử dụng LLM để chuyển đổi câu hỏi của người dùng thành câu tìm kiếm Google tự nhiên
    
    Args:
        user_query: Câu hỏi gốc của người dùng
        conversation_history: Lịch sử hội thoại để có context
    
    Returns:
        str: Câu tìm kiếm đã được tối ưu cho Google
    
    Examples:
        "thông số này là bao nhiêu?" -> "thông số kỹ thuật UPS Liebert APM"
        "nó có mấy cổng?" -> "số lượng cổng kết nối Netsure 210"
    """
    try:
        system_prompt = (
            "Bạn là chuyên gia tối ưu câu truy vấn Google Search.\n"
            "Nhiệm vụ: Chuyển đổi câu hỏi của người dùng thành câu tìm kiếm Google hiệu quả.\n\n"
            "QUY TẮC:\n"
            "1. Thay thế đại từ (này, nó, đó) bằng tên cụ thể dựa vào context\n"
            "2. Thêm từ khóa quan trọng để tìm kiếm chính xác hơn\n"
            "3. Sử dụng ngôn ngữ tự nhiên mà con người thường search\n"
            "4. Không giữ nguyên câu hỏi mơ hồ hoặc thiếu context\n"
            "5. Kết quả phải là câu tìm kiếm ngắn gọn (3-10 từ)\n\n"
            "Trả về JSON: {\"search_query\": \"câu tìm kiếm đã tối ưu\"}"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Thêm context từ lịch sử hội thoại (3 tin nhắn gần nhất)
        context_info = ""
        if conversation_history and len(conversation_history) > 0:
            recent = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
            context_lines = []
            for msg in recent:
                role = "Người dùng" if msg.get("role") == "user" else "Trợ lý"
                content = msg.get("content", "")[:500]  # Giới hạn độ dài
                context_lines.append(f"{role}: {content}")
            context_info = "Context từ lịch sử hội thoại:\n" + "\n".join(context_lines) + "\n\n"
        
        user_prompt = (
            f"{context_info}"
            f"Câu hỏi gốc: \"{user_query}\"\n\n"
            f"Hãy chuyển đổi thành câu tìm kiếm Google tối ưu."
        )
        
        messages.append({"role": "user", "content": user_prompt})
        
        response = oa.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        reformulated = result.get("search_query", "").strip()
        
        if reformulated and len(reformulated) > 5:
            print(f"🔄 Reformulated query: '{user_query}' -> '{reformulated}'")
            return reformulated
        else:
            print(f"⚠️ Reformulation failed, using original query")
            return user_query
            
    except Exception as e:
        print(f"❌ Error reformulating query: {e}")
        return user_query


def google_search(query: str, num_results: int = 5, language: str = "vi") -> List[Dict]:
    """
    Tìm kiếm trên Google và trả về danh sách kết quả
    
    Args:
        query: Câu truy vấn tìm kiếm
        num_results: Số lượng kết quả (tối đa 10)
        language: Ngôn ngữ ('vi' hoặc 'en')
    
    Returns:
        list: Danh sách dict chứa {title, link, snippet}
    """
    credentials = _get_credentials()
    if not credentials:
        print("❌ Không lấy được credentials")
        return []
    
    try:
        request = Request()
        credentials.refresh(request)
        access_token = credentials.token
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "cx": CSE_ID,
            "num": min(num_results, 10),
            "start": 1,
            "hl": language,
            "gl": "vn" if language == "vi" else "us",
        }
        
        if language == "vi":
            params["cr"] = "countryVN"
            params["lr"] = "lang_vi"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        print(f"📡 Calling Google API with query: '{query}'")
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            print(f"✅ Google API returned {len(items)} results")
            
            if not items:
                print(f"⚠️ No items found. Response keys: {list(data.keys())}")
            
            results = []
            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
            return results
        else:
            error_detail = response.text[:200] if response.text else "No error details"
            print(f"❌ Google API error: {response.status_code} - {error_detail}")
            return []
            
    except Exception as e:
        print(f"❌ Lỗi khi search Google: {e}")
        return []


def scrape_page_content(url: str, max_length: int = 3000) -> str:
    """
    Cào nội dung từ một URL
    
    Args:
        url: URL cần cào
        max_length: Độ dài tối đa của nội dung trả về
    
    Returns:
        str: Nội dung text đã được làm sạch
    """
    try:
        response = requests.get(url, headers=SCRAPE_HEADERS, timeout=10, verify=False)
        
        if response.status_code != 200:
            return f"❌ Không thể truy cập (status {response.status_code})"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Xóa các thẻ không cần thiết
        for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script.extract()
        
        # Lấy text
        text = soup.get_text(separator='\n')
        
        # Làm sạch
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Cắt ngắn
        if len(clean_text) > max_length:
            return clean_text[:max_length] + "..."
        return clean_text
        
    except Exception as e:
        return f"❌ Lỗi cào nội dung: {str(e)}"


def google_search_with_content(query: str, num_results: int = 3, scrape_content: bool = True) -> Dict:
    """
    Tìm kiếm Google và tùy chọn cào nội dung chi tiết
    
    Args:
        query: Câu truy vấn
        num_results: Số kết quả (mặc định 3)
        scrape_content: True = cào nội dung, False = chỉ lấy snippet
    
    Returns:
        dict: {
            "response": str (câu trả lời đã format),
            "sources": List[str] (danh sách nguồn với link),
            "results": List[Dict] (kết quả chi tiết)
        }
    """
    print(f"🔍 Đang tìm kiếm Google: {query}")
    
    results = google_search(query, num_results)
    
    if not results:
        print("❌ google_search() returned empty results")
        return {
            "response": "❌ Không tìm thấy kết quả nào trên Google.",
            "sources": [],
            "results": []
        }
    
    print(f"📦 Processing {len(results)} search results")
    
    # Format response
    response_parts = [f"🔍 **Tìm thấy {len(results)} kết quả từ Google:**\n"]
    sources = []
    detailed_results = []
    
    for i, result in enumerate(results, 1):
        title = result['title']
        link = result['link']
        snippet = result['snippet']
        
        # Thêm vào response
        response_parts.append(f"\n**{i}. {title}**")
        response_parts.append(f"📝 {snippet}")
        
        # Thêm vào sources với link
        sources.append(f"- [{title}]({link})")
        
        # Nếu cần scrape content
        content = ""
        if scrape_content:
            print(f"  📄 Đang cào nội dung từ: {link}")
            content = scrape_page_content(link, max_length=2000)
        
        detailed_results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "content": content
        })
    
    response_parts.append("\n\n💡 *Nguồn: Kết quả tìm kiếm từ Google*")
    
    result_dict = {
        "response": "\n".join(response_parts),
        "sources": sources,
        "results": detailed_results
    }
    
    print(f"✅ Returning {len(sources)} sources and {len(detailed_results)} detailed results")
    
    return result_dict


def google_search_simple(query: str, num_results: int = 3) -> str:
    """
    Tìm kiếm Google đơn giản, chỉ trả về text đã format
    Phiên bản đơn giản hơn cho chatbot
    
    Args:
        query: Câu truy vấn
        num_results: Số kết quả
    
    Returns:
        str: Kết quả đã format
    """
    result = google_search_with_content(query, num_results, scrape_content=False)
    return result["response"]
