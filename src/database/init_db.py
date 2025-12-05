# src/database/init_db.py
"""
Script để khởi tạo database schema
Chạy file này để tạo các bảng trong database
"""
from src.database.connect_db import engine, Base
from src.database.models import Category, ProductLine, Product, FileVectorStore


def init_database():
    """Tạo tất cả các bảng trong database"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    init_database()
