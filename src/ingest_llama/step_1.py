from llama_parse import LlamaParse
import os
import asyncio
import nest_asyncio

# Apply nest_asyncio để cho phép chạy async trong event loop đang chạy
nest_asyncio.apply()

async def config_parser_async(pdf_path):
    """Async version for use in FastAPI"""
    # parser = LlamaParse(
    #     result_type="markdown",
    #     auto_mode=True,
    #     auto_mode_trigger_on_image_in_page=True,
    #     auto_mode_trigger_on_table_in_page=True,
    #     skip_diagonal_text=True,
    #     preserve_layout_alignment_across_pages=True,
    #     num_workers=4,
    #     max_timeout=1000,
    # )

    parser = LlamaParse(

        # The parsing tier. Options: fast, cost_effective, agentic, agentic_plus
        tier="agentic",

        # The version of the parsing tier to use. Use 'latest' for the most recent version
        version="latest",

        # Whether to use high resolution OCR (Slow)
        high_res_ocr=True,

        # Adaptive long table. LlamaParse will try to detect long table and adapt the output
        adaptive_long_table=True,

        # Whether to try to extract outlined tables
        outlined_table_extraction=True,

        # Whether to output tables as HTML in the markdown output
        output_tables_as_HTML=True,

        # Whether to use precise bounding box extraction (experimental)
        precise_bounding_box=True,

        # The page separator
        page_separator="\n\n---\n\n",

        # The maximum number of pages to parse
        max_pages=0,
    )
    
    file_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print("Đang parse PDF sang Markdown...")
    parsed_docs = await parser.aparse(pdf_path)
    markdown_documents = parsed_docs.get_markdown_documents(split_by_page=True)
    return markdown_documents, file_name

def config_parser(pdf_path):
    """Sync wrapper - chạy async function trong sync context"""
    try:
        # Kiểm tra xem có event loop đang chạy không
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Nếu có loop đang chạy (trong FastAPI), tạo task mới
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, config_parser_async(pdf_path))
                return future.result()
        else:
            # Nếu không có loop, chạy bình thường
            return asyncio.run(config_parser_async(pdf_path))
    except RuntimeError:
        # Fallback: tạo event loop mới
        return asyncio.run(config_parser_async(pdf_path))