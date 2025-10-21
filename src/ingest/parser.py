import fitz  # PyMuPDF - đọc PDF
import pytesseract  # OCR cho ảnh
from PIL import Image
import pandas as pd
from llama_parse import LlamaParse
import io
import os

# === 1. PDF Parser ===
def parse_pdf(path: str) -> str:
    """Trích xuất text từ PDF"""
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text.strip()


# === 2. Image Parser ===
def parse_image(path: str) -> str:
    """Trích xuất text từ ảnh bằng OCR"""
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+vie")
        return text.strip()
    except Exception as e:
        print(f"[⚠️] OCR lỗi cho file {path}: {e}")
        return ""


# === 3. Excel / CSV Parser ===
def parse_excel(path: str) -> str:
    """Đọc dữ liệu Excel hoặc CSV và chuyển sang text"""
    try:
        if path.lower().endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)
        return df.to_string(index=False)
    except Exception as e:
        print(f"[⚠️] Không đọc được file bảng {path}: {e}")
        return ""


# === 4. Wrapper chọn parser tự động ===
def parse_any(path: str) -> str:
    """Chọn parser tương ứng dựa trên định dạng file"""
    ext = os.path.splitext(path)[1].lower()
    if ext in [".pdf"]:
        return parse_pdf(path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return parse_image(path)
    elif ext in [".xls", ".xlsx", ".csv"]:
        return parse_excel(path)
    else:
        print(f"[⚠️] Không hỗ trợ định dạng {ext}")
        return ""
    
def parser_markdown(pdf_path):
    # 1. Parse PDF sang Markdown
    parser = LlamaParse(
        result_type="markdown",
        auto_mode=True,
        auto_mode_trigger_on_image_in_page=True,
        auto_mode_trigger_on_table_in_page=True,
        skip_diagonal_text=True,
        preserve_layout_alignment_across_pages=True,
        num_workers=4,
        max_timeout=1000,
    )  # hoặc "md"
    print("Đang parse PDF sang Markdown...")
    parsed_docs = parser.load_data(pdf_path)  # Mỗi trang PDF -> 1 Document dạng markdown

    parts = []

    for i, d in enumerate(parsed_docs, start=1):
        parts.append(d.text)

    merged_text = "".join(parts)
    return merged_text