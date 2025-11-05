import os
import time

from chunkr_ai import Chunkr
from pydantic import BaseModel
import dotenv
dotenv.load_dotenv(override=True)

CHUNKR_API_KEY = os.getenv("CHUNKR_API_KEY")
# Initialize the client
client = Chunkr(api_key=CHUNKR_API_KEY)

# Get the task
task = client.get_task(task_id="26f4bc0c-6955-47cb-beea-11a9b15a8ee4")

# Access task info
print(f"Status: {task.status}")
if task.status == "Succeeded" and task.output is not None:
    print(f"Chunks: {len(task.output.chunks)}")
    print(f"First chunk text: {task.output.chunks[2].content}")
    print(f"page number: {task.output.chunks[2].segments[0].page_number}")