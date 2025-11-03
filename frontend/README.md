# Vertiv Chatbot - React Frontend

Giao diện React hiện đại cho Vertiv Chatbot với đầy đủ chức năng như Gradio.

## Tính năng

- 💬 **Chat Interface**: Giao diện chat đẹp mắt, responsive
- 🔍 **Product Filter**: Chọn sản phẩm cụ thể để tìm kiếm
- ⚡ **Strict Mode**: Chế độ chỉ trả lời khi có dữ liệu chính xác
- 📝 **Markdown Support**: Hỗ trợ hiển thị markdown (bold, list, quote, etc.)
- 🎨 **Modern UI**: Thiết kế hiện đại với animations mượt mà
- 📱 **Responsive**: Tương thích mọi thiết bị

## Cấu trúc thư mục

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.jsx    # Component chính
│   │   └── ChatInterface.css    # Styling
│   ├── App.jsx                  # App root
│   ├── App.css
│   ├── main.jsx                 # Entry point
│   └── index.css                # Global styles
├── index.html
├── package.json
└── vite.config.js
```

## Cài đặt

### 1. Cài đặt dependencies

```bash
cd frontend
npm install
```

### 2. Copy PDF files vào public/docs

**Option A: Dùng PowerShell script (Khuyến nghị)**
```powershell
# Từ thư mục gốc project
.\copy-pdfs.ps1
```

**Option B: Copy thủ công**
```powershell
Copy-Item "output\*.pdf" -Destination "frontend\public\docs\" -Recurse -Force
```

**Option C: Copy từ data folder**
```powershell
Get-ChildItem -Path "data" -Filter "*.pdf" -Recurse | Copy-Item -Destination "frontend\public\docs\" -Force
```

### 3. Khởi động Backend (FastAPI)

Mở terminal mới, chạy backend server:

```bash
# Từ thư mục gốc của project
cd d:\project\project1_anhNhat\vertiv_chatbot_r1

# Chạy FastAPI server (port 8000)
uvicorn src.app.server:app --reload --port 8000
```

### 4. Khởi động Frontend (React)

Mở terminal khác:

```bash
cd frontend
npm run dev
```

Frontend sẽ chạy tại: http://localhost:3000

### 5. Kiểm tra PDF files

Kiểm tra PDF có accessible không:
- http://localhost:3000/docs/liebert_apm300_brochure.pdf
- http://localhost:3000/docs/netsure_731_a41_brochure.pdf

Nếu thấy PDF hiển thị → Setup thành công! ✅

## API Endpoint

Backend FastAPI cung cấp endpoint:

- **POST** `/chat`
  ```json
  {
    "query": "Câu hỏi của bạn",
    "product_name": "Liebert Apm" // hoặc null để tìm tất cả
  }
  ```

Response:
```json
{
  "answer": "Câu trả lời từ LLM",
  "sources": [
    "- **file.pdf** (trang 5)\n  > *\"trích dẫn...\"*"
  ]
}
```

## Tech Stack

- **React 18**: UI framework
- **Vite**: Build tool (nhanh hơn Create React App)
- **Axios**: HTTP client
- **React Markdown**: Render markdown
- **Lucide React**: Icons
- **CSS3**: Styling (không dùng framework để nhẹ hơn)

## Scripts

```bash
npm run dev      # Khởi động dev server
npm run build    # Build production
npm run preview  # Preview production build
```

## Tùy chỉnh

### Thay đổi API URL

Sửa file `vite.config.js`:

```js
export default defineConfig({
  server: {
    proxy: {
      '/chat': {
        target: 'http://your-api-url:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### Thêm sản phẩm mới

Sửa mảng `PRODUCTS` trong `ChatInterface.jsx`:

```js
const PRODUCTS = [
  'Tất cả',
  'Sản phẩm mới của bạn',
  // ...
]
```

## So sánh với Gradio

| Tính năng | Gradio | React Frontend |
|-----------|--------|----------------|
| Chat Interface | ✅ | ✅ |
| Product Filter | ✅ | ✅ |
| Strict Mode | ✅ | ✅ |
| Markdown Display | ✅ | ✅ |
| Custom Styling | ⚠️ Hạn chế | ✅ Hoàn toàn |
| Responsive | ✅ | ✅ |
| Deployment | Dễ | Cần build |
| Performance | Tốt | Rất tốt |

## Troubleshooting

### CORS Error

Nếu gặp lỗi CORS, kiểm tra:
1. Backend đã thêm CORS middleware chưa
2. Frontend URL có trong `allow_origins` không

### Port đã được sử dụng

```bash
# Thay đổi port trong vite.config.js
server: {
  port: 3001  // port khác
}
```

## License

MIT
