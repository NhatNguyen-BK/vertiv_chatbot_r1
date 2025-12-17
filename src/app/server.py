# src/app/server.py
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil
import hashlib

from src.app.options.query import answer  # tái dùng hàm đã chạy OK
from src.database.connect_db import SessionLocal
from src.database import crud, models
from src.ingest_llama.index_qdrant import index_one_file

app = FastAPI(title="Vertiv Chatbot API")

# Thêm CORS middleware để React frontend có thể gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== DEPENDENCY ====================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== PYDANTIC MODELS ====================
class Ask(BaseModel):
    query: str
    file_names: List[str] | None = None  # None = tìm tất cả, hoặc list file names để filter


class CategoryCreate(BaseModel):
    id: str
    name: str


class ProductLineCreate(BaseModel):
    id: str
    name: str
    category_id: str


class ProductCreate(BaseModel):
    id: str
    name: str
    product_line_id: str


class FileCreate(BaseModel):
    id: str
    name: str
    product_id: str


class CategoryResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class ProductLineResponse(BaseModel):
    id: str
    name: str
    category_id: str

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: str
    name: str
    product_line_id: str

    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    id: str
    name: str
    product_id: str

    class Config:
        from_attributes = True


# ==================== CHAT ENDPOINT ====================
@app.post("/chat")
def chat(req: Ask):
    reply, sources, chunks = answer(req.query, file_names=req.file_names)
    return {
        "answer": reply,
        "sources": sources,
        "chunks": chunks
    }


# ==================== CATEGORY ENDPOINTS ====================
@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Tạo category mới"""
    existing = crud.get_category(db, category.id)
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    return crud.create_category(db, category.id, category.name)


@app.get("/categories", response_model=List[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    """Lấy tất cả categories"""
    return crud.get_all_categories(db)


@app.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: str, db: Session = Depends(get_db)):
    """Lấy category theo id"""
    category = crud.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@app.delete("/categories/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db)):
    """Xóa category"""
    success = crud.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}


# ==================== PRODUCT LINE ENDPOINTS ====================
@app.post("/product-lines", response_model=ProductLineResponse)
def create_product_line(product_line: ProductLineCreate, db: Session = Depends(get_db)):
    """Tạo product line mới"""
    existing = crud.get_product_line(db, product_line.id)
    if existing:
        raise HTTPException(status_code=400, detail="Product line already exists")
    return crud.create_product_line(db, product_line.id, product_line.name, product_line.category_id)


@app.get("/product-lines", response_model=List[ProductLineResponse])
def get_product_lines(category_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Lấy tất cả product lines, có thể filter theo category_id"""
    if category_id:
        return crud.get_product_lines_by_category(db, category_id)
    return crud.get_all_product_lines(db)


@app.get("/product-lines/{product_line_id}", response_model=ProductLineResponse)
def get_product_line(product_line_id: str, db: Session = Depends(get_db)):
    """Lấy product line theo id"""
    product_line = crud.get_product_line(db, product_line_id)
    if not product_line:
        raise HTTPException(status_code=404, detail="Product line not found")
    return product_line


@app.delete("/product-lines/{product_line_id}")
def delete_product_line(product_line_id: str, db: Session = Depends(get_db)):
    """Xóa product line"""
    success = crud.delete_product_line(db, product_line_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product line not found")
    return {"message": "Product line deleted successfully"}


# ==================== PRODUCT ENDPOINTS ====================
@app.post("/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Tạo product mới"""
    existing = crud.get_product(db, product.id)
    if existing:
        raise HTTPException(status_code=400, detail="Product already exists")
    return crud.create_product(db, product.id, product.name, product.product_line_id)


@app.get("/products", response_model=List[ProductResponse])
def get_products(product_line_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Lấy tất cả products, có thể filter theo product_line_id"""
    if product_line_id:
        return crud.get_products_by_product_line(db, product_line_id)
    return crud.get_all_products(db)


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Lấy product theo id"""
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/products/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db)):
    """Xóa product"""
    success = crud.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


# ==================== FILE ENDPOINTS ====================
@app.post("/files", response_model=FileResponse)
def create_file(file: FileCreate, db: Session = Depends(get_db)):
    """Tạo file mới"""
    existing = crud.get_file(db, file.id)
    if existing:
        raise HTTPException(status_code=400, detail="File already exists")
    return crud.create_file(db, file.id, file.name, file.product_id)


@app.get("/files", response_model=List[FileResponse])
def get_files(product_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Lấy tất cả files, có thể filter theo product_id"""
    if product_id:
        return crud.get_files_by_product(db, product_id)
    return crud.get_all_files(db)


@app.get("/files/{file_id}", response_model=FileResponse)
def get_file(file_id: str, db: Session = Depends(get_db)):
    """Lấy file theo id"""
    file = crud.get_file(db, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file


@app.delete("/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    """Xóa file"""
    success = crud.delete_file(db, file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted successfully"}


# ==================== UPLOAD & COPY FILE ====================
@app.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    category_id: str = Form(...),
    category_name: str = Form(...),
    product_line_id: str = Form(...),
    product_line_name: str = Form(...),
    product_id: str = Form(...),
    product_name: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload file PDF theo flow:
    1. Lưu file tạm
    2. Index vào Qdrant (nếu thất bại thì dừng)
    3. Lưu vào Database
    4. Copy vào frontend/public/docs/
    """
    temp_file_path = None
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # 1. Đọc file content
        file_content = await file.read()
        file_hash = hashlib.md5(file_content).hexdigest()[:16]
        
        # 2. Lưu file tạm để index vào Qdrant
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../.."))
        temp_dir = os.path.join(project_root, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        
        # 3. Index vào Qdrant (BƯỚC QUAN TRỌNG - nếu fail thì dừng)
        try:
            num_chunks = index_one_file(temp_file_path, skip_db=True)
            if num_chunks == 0:
                raise Exception("No chunks indexed")
        except Exception as e:
            # Xóa file tạm nếu index thất bại
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to index file to Qdrant: {str(e)}"
            )
        
        # 4. Nếu index Qdrant thành công, lưu vào Database
        category = crud.get_or_create_category(db, category_id, category_name)
        product_line = crud.get_or_create_product_line(
            db, product_line_id, product_line_name, category_id
        )
        product = crud.get_or_create_product(
            db, product_id, product_name, product_line_id
        )
        db_file = crud.get_or_create_file(
            db, file_hash, file.filename, product_id
        )
        
        # 5. Copy file vào frontend/public/docs/
        public_docs_dir = os.path.join(project_root, "frontend", "public", "docs")
        os.makedirs(public_docs_dir, exist_ok=True)
        
        final_file_path = os.path.join(public_docs_dir, file.filename)
        shutil.copy2(temp_file_path, final_file_path)
        
        # 6. Xóa file tạm
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        return {
            "message": "File uploaded and indexed successfully",
            "file": {
                "id": db_file.id,
                "name": db_file.name,
                "path": f"/docs/{file.filename}",
                "product_id": product_id,
                "chunks_indexed": num_chunks
            },
            "category": {"id": category.id, "name": category.name},
            "product_line": {"id": product_line.id, "name": product_line.name},
            "product": {"id": product.id, "name": product.name}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup nếu có lỗi
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ==================== GET PRODUCT HIERARCHY ====================
@app.get("/product-hierarchy")
def get_product_hierarchy(db: Session = Depends(get_db)):
    """
    Lấy cấu trúc phân cấp: Category > ProductLine > Product
    Dùng cho dropdown trong FE
    """
    categories = crud.get_all_categories(db)
    result = []
    
    for category in categories:
        product_lines = crud.get_product_lines_by_category(db, category.id)
        lines_data = []
        
        for product_line in product_lines:
            products = crud.get_products_by_product_line(db, product_line.id)
            products_data = [
                {"id": p.id, "name": p.name} for p in products
            ]
            
            lines_data.append({
                "id": product_line.id,
                "name": product_line.name,
                "products": products_data
            })
        
        result.append({
            "id": category.id,
            "name": category.name,
            "product_lines": lines_data
        })
    
    return result