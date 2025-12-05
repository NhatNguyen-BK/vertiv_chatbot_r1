# API và Database Integration

## Tổng quan

Hệ thống đã được tích hợp với PostgreSQL database để quản lý thông tin sản phẩm và tự động đồng bộ khi index tài liệu.

## Cấu trúc Database

```
Category (dc_power, thermal, ups)
  └─ ProductLine (netsure_731, liebert_crv, ...)
      └─ Product (A41, CRV4, ...)
          └─ FileVectorStore (file PDF đã index)
```

## Khởi tạo Database

```bash
cd src/database
python init_db.py
```

## API Endpoints

### 1. Chat (có sẵn)
```
POST /chat
Body: {"query": "...", "product_name": "..."}
```

### 2. Categories
```
GET    /categories              # Lấy tất cả categories
GET    /categories/{id}         # Lấy category theo id
POST   /categories              # Tạo category mới
DELETE /categories/{id}         # Xóa category
```

### 3. Product Lines
```
GET    /product-lines           # Lấy tất cả product lines
GET    /product-lines?category_id=xxx  # Filter theo category
GET    /product-lines/{id}      # Lấy product line theo id
POST   /product-lines           # Tạo product line mới
DELETE /product-lines/{id}      # Xóa product line
```

### 4. Products
```
GET    /products                # Lấy tất cả products
GET    /products?product_line_id=xxx  # Filter theo product line
GET    /products/{id}           # Lấy product theo id
POST   /products                # Tạo product mới
DELETE /products/{id}           # Xóa product
```

### 5. Files
```
GET    /files                   # Lấy tất cả files
GET    /files?product_id=xxx    # Filter theo product
GET    /files/{id}              # Lấy file theo id
POST   /files                   # Tạo file mới
DELETE /files/{id}              # Xóa file
```

## Cách sử dụng

### 1. Index tài liệu (tự động lưu vào DB)

```bash
cd src/ingest_llama
python index_qdrant.py
```

Sau khi index, hệ thống sẽ tự động:
- Tạo/cập nhật Category
- Tạo/cập nhật ProductLine
- Tạo/cập nhật Product
- Tạo/cập nhật FileVectorStore

### 2. Chạy API server

```bash
cd src/app
uvicorn server:app --reload
```

### 3. Test API

```bash
# Lấy danh sách categories
curl http://localhost:8000/categories

# Lấy danh sách products
curl http://localhost:8000/products

# Chat với bot (sẽ lấy products từ DB)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "có những sản phẩm gì?"}'
```

### 4. Tạo product thủ công (nếu cần)

```bash
# Tạo category
curl -X POST http://localhost:8000/categories \
  -H "Content-Type: application/json" \
  -d '{"id": "dc_power", "name": "DC Power"}'

# Tạo product line
curl -X POST http://localhost:8000/product-lines \
  -H "Content-Type: application/json" \
  -d '{"id": "netsure_731", "name": "Netsure 731", "category_id": "dc_power"}'

# Tạo product
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{"id": "netsure_731_a41", "name": "A41", "product_line_id": "netsure_731"}'
```

## Thay đổi chính

### 1. `src/database/crud.py` (MỚI)
- Các hàm CRUD cho tất cả các bảng
- `get_or_create_*` để tránh duplicate

### 2. `src/app/server.py`
- Thêm endpoints cho Category, ProductLine, Product, File
- Sử dụng SQLAlchemy ORM với FastAPI Depends

### 3. `src/ingest_llama/index_qdrant.py`
- Thêm hàm `save_to_database()` 
- Tự động lưu thông tin sau khi index

### 4. `src/app/options/tools.py`
- Thay hardcode `PRODUCTS` bằng `get_products_from_db()`
- Fallback về danh sách mặc định nếu DB lỗi

## Lưu ý

1. **Env variables**: Đảm bảo có `DB_POSTGRES_URL` trong `.env`
2. **Migration**: Chạy `init_db.py` trước khi sử dụng
3. **Cascade delete**: Xóa Category sẽ xóa tất cả con cháu
4. **ID format**: Sử dụng snake_case (vd: `dc_power`, `netsure_731`)
