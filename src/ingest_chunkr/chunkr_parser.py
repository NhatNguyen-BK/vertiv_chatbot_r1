import os
import time
from chunkr_ai import Chunkr
from llama_index.core import Document
import dotenv

dotenv.load_dotenv(override=True)

CHUNKR_API_KEY = os.getenv("CHUNKR_API_KEY")
client = Chunkr(api_key=CHUNKR_API_KEY)


def parse_chunk(pdf_path):
    """Parse PDF using Chunkr and return LlamaIndex Documents"""
    # Create parse task
    task = client.create_task(file=pdf_path)
    print(f"Created task: {task}")
    # Poll until task completes
    max_wait = 300  # 5 minutes timeout
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Refresh task status
        task = client.get_task(task_id=task.task_id)
        
        if task.status == "Succeeded":
            break
        elif task.status == "Failed":
            raise Exception(f"Parsing failed: {task.message}")
        
        time.sleep(2)  # Wait 2 seconds before checking again
    else:
        raise TimeoutError("Parsing timeout after 5 minutes")
    
    # Extract documents
    if task.output is None or not task.output.chunks:
        return []
    
    documents = []
    for chunk in task.output.chunks:
        # Get page number from first segment
        page_number = None
        if chunk.segments:
            page_number = chunk.segments[0].page_number
        
        documents.append(
            Document(
                text=chunk.content,
                metadata={
                    "page": page_number,
                    "chunk_id": chunk.chunk_id,
                    "file_name": os.path.splitext(os.path.basename(pdf_path))[0]
                }
            )
        )
    
    # Save to markdown file
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    file_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_file = f"{output_dir}/{file_name}.md"
    
    with open(output_file, "w", encoding="utf-8") as f:
        for idx, doc in enumerate(documents, start=1):
            f.write(f"# Chunk {idx}\n")
            f.write(doc.text + "\n\n\n\n")
    
    return documents