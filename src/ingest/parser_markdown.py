from markitdown import MarkItDown
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Khởi tạo OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Khởi tạo MarkItDown với LLM model
md = MarkItDown(
    llm_client=openai_client,  # Thêm OpenAI client
    llm_model="gpt-4o-mini",   # Model để mô tả hình ảnh, bảng phức tạp
    enable_plugins=False
)

# Convert file PDF sang Markdown (LLM sẽ tự động xử lý hình ảnh/bảng)
result = md.convert("D:/project/project1_anhNhat/vertiv_chatbot_r1/data/DC_Power/netsure_210/netsure_210_brochure.pdf")

# Lấy nội dung Markdown
markdown_content = result.text_content

# Lưu vào file .md
output_file = "output.md"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"Markdown đã được lưu vào {output_file}")