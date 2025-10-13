# src/app/server.py
from fastapi import FastAPI
from pydantic import BaseModel
from .query import answer  # tái dùng hàm đã chạy OK

app = FastAPI(title="Vertiv Chatbot API")

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