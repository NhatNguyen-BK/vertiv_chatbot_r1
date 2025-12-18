# ✅ Google Fallback - LLM Processing Update

## 🎯 Thay đổi

**Trước:** Khi Google Fallback được kích hoạt, kết quả Google được format trực tiếp và trả về.

**Sau:** Kết quả Google được **đưa vào LLM để tổng hợp** như RAG thông thường.

## 🔄 Flow mới

```
User Query
    ↓
RAG Search (Qdrant)
    ↓
Không có kết quả + Google Fallback ON
    ↓
Google Search (top 5 results)
    ↓
Lấy snippets/content làm contexts
    ↓
Đưa vào LLM (giống RAG)
    ↓
LLM tổng hợp + citations
    ↓
Trả về câu trả lời tự nhiên
```

## 📝 Code changes

### File: `query.py`

#### Thêm hàm mới: `_google_fallback_answer(query)`

Hàm này:
1. Gọi `handle_google_search()` để lấy 5 kết quả
2. Dùng snippets/content làm contexts
3. Đánh số contexts: `[Nguồn 1], [Nguồn 2], ...`
4. Đưa vào LLM với system prompt tương tự RAG
5. Parse JSON response với answer + citations
6. Format sources với links và quotes
7. Thêm note: "*ℹ️ Thông tin được tổng hợp từ kết quả tìm kiếm trên Internet*"

#### Cập nhật: `answer()` function

```python
if use_google_fallback and không_có_kết_quả:
    return _google_fallback_answer(query)  # Thay vì format trực tiếp
```

## 💡 Ví dụ

### Input
```
User: "What is artificial intelligence?"
Toggle: Google Fallback = ON
```

### Output (sau khi LLM xử lý)
```
Artificial intelligence (AI) là một lĩnh vực của khoa học máy tính 
tập trung vào việc tạo ra các hệ thống có khả năng thực hiện các 
nhiệm vụ thường yêu cầu trí tuệ con người. AI bao gồm machine learning, 
deep learning, và natural language processing. Các hệ thống AI có thể 
học hỏi từ dữ liệu và cải thiện hiệu suất theo thời gian.

*ℹ️ Thông tin được tổng hợp từ kết quả tìm kiếm trên Internet*

---
**Nguồn tham khảo:**
- [What is Artificial Intelligence (AI)? - IBM](https://www.ibm.com/...)
  > *"Artificial intelligence leverages computers and machines..."*
- [Artificial intelligence - Wikipedia](https://en.wikipedia.org/...)
  > *"AI is intelligence exhibited by machines..."*
```

## ✨ Ưu điểm

1. **Câu trả lời tự nhiên hơn**: LLM tổng hợp thông tin thay vì list raw results
2. **Có citations**: Giống RAG, có trích dẫn chính xác
3. **Consistent UX**: Format giống khi trả lời từ database
4. **Intelligent**: LLM filter và tổng hợp thông tin quan trọng

## 🧪 Testing

```bash
python test_google_fallback.py
```

Hoặc test thủ công:
1. Bật "Google Fallback" toggle
2. Hỏi câu không có trong DB: "What is blockchain?"
3. Verify: Câu trả lời được tổng hợp tự nhiên, không phải list results

## 🔧 Tùy chỉnh

### Số lượng kết quả Google
```python
google_result = handle_google_search(query, num_results=5)  # 5 → 10
```

### System prompt
Chỉnh sửa trong `_google_fallback_answer()`:
```python
sys = "Bạn là trợ lý thông minh. ..."  # Customize prompt
```

### Note footer
```python
reply_with_note = f"{reply}\n\n*ℹ️ Tùy chỉnh note của bạn*"
```

## ✅ Hoàn tất

Google Fallback giờ đây hoạt động giống như RAG thông thường, với:
- ✅ LLM tổng hợp thông tin
- ✅ Citations rõ ràng
- ✅ Câu trả lời tự nhiên
- ✅ Consistent với RAG flow
