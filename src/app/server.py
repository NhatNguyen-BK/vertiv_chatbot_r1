# src/app/server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.app.options.query import answer  # tái dùng hàm đã chạy OK

app = FastAPI(title="Vertiv Chatbot API")

# Thêm CORS middleware để React frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Ask(BaseModel):
    query: str
    product_name: str | None = None  # None = tìm tất cả sản phẩm

@app.post("/chat")
def chat(req: Ask):
    reply, sources = answer(req.query, product_name=req.product_name)
    return {
        "answer": reply,
        "sources": sources
    }