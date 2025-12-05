# Frontend Updates - Dynamic Products & Document Upload

## ✅ Những gì đã thay đổi

### 1. **ChatInterface.jsx**
- ❌ Xóa hardcode `PRODUCTS` array
- ✅ Thêm `loadProducts()` để fetch từ API `/product-lines`
- ✅ Dynamic product selection dropdown
- ✅ Fallback về danh sách mặc định nếu API lỗi

### 2. **UploadManager.jsx** (MỚI)
Component quản lý upload tài liệu với các tính năng:
- 📁 Chọn hoặc tạo mới Category
- 📦 Chọn hoặc tạo mới Product Line
- 🏷️ Chọn hoặc tạo mới Product
- 📄 Upload file PDF
- ✅ Tự động copy file vào `frontend/public/docs/`
- ✅ Lưu thông tin vào database

### 3. **App.jsx**
- 🔄 Thêm tab navigation: **Chat** và **Quản lý tài liệu**
- 📱 Responsive design

### 4. **Backend API**
#### `POST /upload-file`
Upload PDF và tự động:
1. Tạo/lấy Category, ProductLine, Product
2. Lưu file vào `frontend/public/docs/`
3. Lưu metadata vào database

#### `GET /product-hierarchy`
Trả về cấu trúc phân cấp đầy đủ cho dropdown

## 🚀 Cách sử dụng

### 1. Khởi động Backend
```bash
cd src/app
uvicorn server:app --reload --port 8000
```

### 2. Khởi động Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Upload tài liệu mới

#### Cách 1: Chọn sản phẩm có sẵn
1. Vào tab **"Quản lý tài liệu"**
2. Chọn Category (vd: DC Power)
3. Chọn Product Line (vd: Netsure 731)
4. Chọn Product (vd: A41)
5. Chọn file PDF
6. Click **"Upload tài liệu"**

#### Cách 2: Tạo sản phẩm mới
1. Vào tab **"Quản lý tài liệu"**
2. **Category mới:**
   - ID: `thermal` (snake_case)
   - Name: `Thermal` (Title Case)
3. **Product Line mới:**
   - ID: `liebert_crv4` (snake_case)
   - Name: `Liebert CRV4` (Title Case)
4. **Product mới:**
   - ID: `liebert_crv4_model_a` (snake_case)
   - Name: `Model A` (Title Case)
5. Chọn file PDF
6. Click **"Upload tài liệu"**

### 4. Sử dụng Chat
1. Vào tab **"Chat"**
2. Dropdown sản phẩm sẽ tự động load từ database
3. Chọn sản phẩm hoặc "Tất cả"
4. Chat như bình thường

## 📂 Cấu trúc file sau khi upload

```
frontend/
  public/
    docs/
      netsure_731_a41_brochure.pdf     ✅ File được copy vào đây
      liebert_crv4_manual.pdf          ✅ File được copy vào đây
      ...

Database:
  category: thermal
    └─ product_line: liebert_crv4
        └─ product: liebert_crv4_model_a
            └─ file: liebert_crv4_manual.pdf
```

## 🔄 Flow hoàn chỉnh

### Upload Document Flow:
```
User uploads PDF
    ↓
POST /upload-file
    ↓
1. Validate PDF file
2. Get/Create Category
3. Get/Create ProductLine
4. Get/Create Product
5. Copy file to frontend/public/docs/
6. Save FileVectorStore to DB
    ↓
Success! File available at /docs/{filename}
```

### Chat Flow:
```
User opens Chat
    ↓
GET /product-lines
    ↓
Populate dropdown
    ↓
User selects product & asks question
    ↓
POST /chat
    ↓
Response with PDF links
    ↓
User clicks "Xem PDF" → Opens in PdfViewer
```

## 🎨 UI Features

### Tab Navigation
- 💬 **Chat**: Giao diện chat với bot
- 📤 **Quản lý tài liệu**: Upload và tạo cấu trúc sản phẩm

### Upload Manager
- ✅ Form validation
- ✅ Real-time status messages
- ✅ Hierarchical dropdowns
- ✅ Create new or select existing
- ✅ PDF file picker
- ✅ Upload progress indicator

### Chat Interface
- ✅ Dynamic product dropdown từ DB
- ✅ Fallback nếu API lỗi
- ✅ PDF viewer integration

## ⚠️ Lưu ý

1. **File naming**: Nên dùng tên file có ý nghĩa, không dấu tiếng Việt
2. **ID format**: Luôn dùng snake_case (vd: `dc_power`, `netsure_731`)
3. **Name format**: Dùng Title Case (vd: `DC Power`, `Netsure 731`)
4. **PDF location**: File phải nằm trong `frontend/public/docs/` để FE đọc được
5. **CORS**: Đảm bảo backend cho phép CORS từ frontend port

## 🐛 Troubleshooting

### Products không hiển thị trong dropdown?
- Kiểm tra backend đang chạy (`http://localhost:8000`)
- Check console browser xem có lỗi API không
- Verify database có dữ liệu: `GET http://localhost:8000/product-lines`

### Upload thất bại?
- Kiểm tra file có phải PDF không
- Verify đã điền đủ thông tin Category/ProductLine/Product
- Check backend logs để xem lỗi chi tiết

### PDF không hiển thị trong viewer?
- Kiểm tra file đã được copy vào `frontend/public/docs/`
- Verify đường dẫn trong database khớp với file name
- Check browser console xem có lỗi 404 không

## 📝 Testing

```bash
# Test upload API
curl -X POST http://localhost:8000/upload-file \
  -F "file=@test.pdf" \
  -F "category_id=dc_power" \
  -F "category_name=DC Power" \
  -F "product_line_id=netsure_731" \
  -F "product_line_name=Netsure 731" \
  -F "product_id=netsure_731_a41" \
  -F "product_name=A41"

# Test product hierarchy
curl http://localhost:8000/product-hierarchy

# Test product lines
curl http://localhost:8000/product-lines
```
