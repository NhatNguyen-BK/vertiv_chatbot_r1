# Cập nhật: Tích hợp PDF Viewer với Citation Highlighting

## 🎯 Tính năng mới

Đã thêm **PDF Viewer** với khả năng:
- ✅ Hiển thị PDF bên cạnh chat
- ✅ Tự động tìm và highlight đoạn trích dẫn từ LLM
- ✅ Scroll tự động đến vị trí được highlight
- ✅ Hỗ trợ multiple sources
- ✅ Split-view responsive

## 📦 Dependencies mới

Đã thêm vào `package.json`:
```json
"react-pdf": "^7.7.0",
"pdfjs-dist": "^3.11.174"
```

## 🆕 Files mới

1. **PdfViewer.jsx** - Component hiển thị PDF với highlight
2. **PdfViewer.css** - Styling cho PDF viewer

## 🔧 Files đã cập nhật

### 1. ChatInterface.jsx
- Thêm state `showPdfViewer`, `pdfData`
- Thêm function `parseSource()` để parse source text
- Thêm function `handleSourceClick()` để mở PDF
- Thêm nút "Xem PDF" cho mỗi source
- Thêm PDF viewer panel bên phải

### 2. ChatInterface.css
- Thêm `.chat-layout` để hỗ trợ split view
- Thêm `.source-actions` cho các nút xem PDF
- Thêm `.pdf-viewer-panel` cho panel PDF
- Cập nhật responsive styles

## 🚀 Cách sử dụng

### 1. Cài đặt dependencies mới
```bash
cd frontend
npm install
```

### 2. Thêm PDF files vào public folder
Tạo folder `frontend/public/docs/` và copy các file PDF vào đó:
```
frontend/
└── public/
    └── docs/
        ├── liebert_apm300_brochure.pdf
        ├── netsure_731_brochure.pdf
        └── ...
```

### 3. Chạy ứng dụng
```bash
# Terminal 1: Backend
uvicorn src.app.server:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

## 💡 Cách hoạt động

1. **User gửi câu hỏi** → Backend xử lý qua RAG
2. **LLM trả về** answer + citations với format:
   ```
   - **file.pdf** (trang 5)
     > *"đoạn trích dẫn chính xác"*
   ```
3. **Frontend hiển thị** câu trả lời + nút "Xem PDF"
4. **User click nút** → Mở PDF viewer bên phải
5. **PDF Viewer**:
   - Load PDF file
   - Tìm đoạn text khớp với trích dẫn
   - Highlight màu vàng cam
   - Scroll tự động đến vị trí

## 🎨 Thuật toán Highlighting

```javascript
// 1. Tách trích dẫn thành các từ
searchWords = ["Liebert", "APM", "300", "kVA"]

// 2. Gom text spans trong PDF thành dòng
lines = [
  { text: "Liebert APM 300 kVA UPS System", spans: [...] },
  { text: "Other text...", spans: [...] }
]

// 3. Đếm số từ khớp mỗi dòng
line1: 4 matches ✅ (best match)
line2: 0 matches

// 4. Highlight dòng có nhiều match nhất
→ Highlight "Liebert APM 300 kVA UPS System"
```

## 📁 Cấu trúc file PDF

Backend cần map file names sang đường dẫn:
```javascript
const pdfPath = `/docs/${parsed.file}` // → /docs/liebert_apm300_brochure.pdf
```

Hoặc có thể tạo API endpoint để serve PDF từ backend.

## ⚙️ Tùy chỉnh

### Thay đổi màu highlight
Sửa trong `PdfViewer.jsx`:
```javascript
span.style.background = '#FFA50080' // Màu cam với opacity 50%
span.style.color = '#000'
span.style.fontWeight = 'bold'
```

### Thay đổi vị trí scroll
```javascript
const targetScrollTop = spanTop - 200 // offset 200px từ top
```

### Thêm API để serve PDF
Trong `server.py`:
```python
from fastapi.responses import FileResponse

@app.get("/pdf/{filename}")
async def get_pdf(filename: str):
    pdf_path = f"./data/{filename}"
    return FileResponse(pdf_path, media_type='application/pdf')
```

Sau đó trong React:
```javascript
const pdfPath = `http://localhost:8000/pdf/${parsed.file}`
```

## 🐛 Troubleshooting

### PDF không load
- Kiểm tra file có trong `public/docs/` chưa
- Kiểm tra console browser xem lỗi gì
- Đảm bảo file name khớp với backend

### Không highlight được
- Mở console xem log "Search words", "Line matches"
- Kiểm tra trích dẫn có chính xác không
- PDF có thể là image-based (cần OCR)

### CORS error với PDF
- Thêm CORS cho static files trong backend
- Hoặc serve PDF qua backend API

## 📊 Performance

- Lazy loading: Chỉ load PDF khi cần
- Multiple pages: Render tất cả pages một lúc
- Caching: Browser tự cache PDF files
- Smooth scroll: Dùng `scrollIntoView({ behavior: 'smooth' })`

## 🎯 Next Steps

Có thể mở rộng:
- [ ] Cache parsed PDF để không phải parse lại
- [ ] Thêm zoom in/out cho PDF
- [ ] Download PDF button
- [ ] Copy citation text
- [ ] Multiple PDF tabs
- [ ] Search box trong PDF
- [ ] Annotation/notes

## 📝 Notes

- PDF.js worker được load từ CDN qua `import.meta.url`
- Split view tự động responsive trên mobile
- Hỗ trợ multiple citations → multiple "Xem PDF" buttons
