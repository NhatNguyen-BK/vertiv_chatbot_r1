import asyncio
import os
from llama_parse import LlamaParse
import os
from dotenv import load_dotenv
load_dotenv()

# --- CẤU HÌNH API KEY ---
# Bạn có thể điền trực tiếp key vào đây hoặc set biến môi trường
# os.environ["LLAMA_CLOUD_API_KEY"] = "llx-..." 
os.environ["LLAMA_CLOUD_API_KEY"] = os.getenv("LLAMA_API_KEY")
async def parse_doc_with_local_images(pdf_path, output_image_dir="hinh_anh_local"):
    """
    Hàm xử lý PDF:
    1. Gửi lên LlamaParse lấy JSON
    2. Tải ảnh về thư mục local
    3. Thay thế link ảnh online trong Markdown bằng đường dẫn local
    """
    
    # 1. Khởi tạo Parser
    # Nếu chưa set API Key ở trên, hãy thêm tham số api_key="llx-..." vào bên dưới
    parser = LlamaParse(
        result_type="markdown", 
        verbose=True
    )

    print(f"--- Bắt đầu xử lý file: {pdf_path} ---")
    
    # 2. Lấy kết quả dạng JSON
    # Dùng aget_json để lấy dữ liệu thô (text + metadata ảnh)
    try:
        json_objs = await parser.aget_json(pdf_path)
    except Exception as e:
        print(f"Lỗi khi gửi file lên server: {e}")
        return None
    
    # 3. Tải ảnh về máy
    print(f"--- Đang tải ảnh về thư mục: {output_image_dir} ---")
    # Tạo thư mục nếu chưa có
    if not os.path.exists(output_image_dir):
        os.makedirs(output_image_dir)
        
    # Hàm aget_images tự động tải và trả về đường dẫn file đã lưu
    downloaded_images = parser.get_images(json_objs, download_path=output_image_dir)
    
    # 4. GẮN LINK ẢNH VÀO MARKDOWN
    print("--- Đang cập nhật đường dẫn ảnh trong Markdown ---")
    final_markdown = ""
    
    # print keys of the first object to debug
    # Create a map of image name -> local path for easy lookup
    img_map = {img["name"]: img["path"] for img in downloaded_images}

    for result in json_objs:
        # Check if 'pages' key exists (standard structure)
        if "pages" in result:
            pages_list = result["pages"]
        else:
            # Fallback or if the structure is different (e.g. single page object)
            pages_list = [result]

        for page in pages_list:
            if "md" not in page:
                continue
                
            page_md = page["md"] # Nội dung Markdown gốc của trang
            
            # Get images specific to this page
            page_images = page.get("images", [])
            
            for img_info in page_images:
                img_name = img_info["name"]
                
                if img_name in img_map:
                    img_path = img_map[img_name]
                    # Chuẩn hóa đường dẫn cho Markdown (đổi \ thành / để tránh lỗi hiển thị trên Windows)
                    img_path_clean = img_path.replace(os.sep, "/")
                    
                    # Tìm và thay thế tên ảnh trong text
                    if img_name in page_md:
                        print(f"Debug: Replacing {img_name} with {img_path_clean}")
                        # Markdown ảnh thường là: ![desc](img_name) -> đổi thành ![desc](img_path_clean)
                        page_md = page_md.replace(f"({img_name})", f"({img_path_clean})")
                    else:
                        # Nếu ảnh không có trong markdown, ta sẽ chèn vào cuối trang
                        print(f"Debug: Image {img_name} not found in MD text. Appending to end of page.")
                        page_md += f"\n\n![{img_name}]({img_path_clean})\n"
            
            final_markdown += page_md + "\n\n"

    print("--- Xử lý hoàn tất! ---")
    return final_markdown

# --- HÀM MAIN ---
async def main():
    # 1. Điền tên file PDF của bạn ở đây
    input_pdf = "D:/project/project1_anhNhat/vertiv_chatbot_r1/data/Test Report TUV IEC62040.1.pdf" 
    output_md = "ket_qua_co_anh.md"

    # Kiểm tra file tồn tại
    if not os.path.exists(input_pdf):
        print(f"Lỗi: Không tìm thấy file '{input_pdf}'")
        return

    # 2. Gọi hàm xử lý
    markdown_result = await parse_doc_with_local_images(input_pdf)

    # 3. Lưu kết quả ra file
    if markdown_result:
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(markdown_result)
        print(f"\n=> Đã lưu kết quả vào: {output_md}")
        print("=> Bạn hãy mở file .md này bằng VSCode hoặc Obsidian để xem ảnh.")

# --- ĐIỂM BẮT ĐẦU CỦA SCRIPT ---
if __name__ == "__main__":
    # Đây là chuẩn chạy async trong file .py
    asyncio.run(main())