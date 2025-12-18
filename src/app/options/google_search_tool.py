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

# Tắt cảnh báo SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            items = response.json().get("items", [])
            results = []
            for item in items:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
            return results
        else:
            print(f"❌ Google API error: {response.status_code}")
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
        return {
            "response": "❌ Không tìm thấy kết quả nào trên Google.",
            "sources": [],
            "results": []
        }
    
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
    
    return {
        "response": "\n".join(response_parts),
        "sources": sources,
        "results": detailed_results
    }


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
