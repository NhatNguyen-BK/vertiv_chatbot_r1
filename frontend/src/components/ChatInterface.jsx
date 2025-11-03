import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, FileText } from 'lucide-react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import PdfViewer from './PdfViewer'
import './ChatInterface.css'

const PRODUCTS = [
  'Tất cả',
  'Netsure 210',
  'Netsure 531',
  'Netsure 731',
  'Liebert Apm',
  'Liebert Exs',
  'Liebrt Mtp',
  'Liebert Crv',
  'Libert Pex3',
  'Libert Pex4'
]

function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [selectedProduct, setSelectedProduct] = useState('Tất cả')
  const [strictMode, setStrictMode] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showPdfViewer, setShowPdfViewer] = useState(false)
  const [pdfData, setPdfData] = useState({ url: '', searchTexts: [], page: null })
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!inputMessage.trim() || isLoading) return

    const userMessage = {
      role: 'user',
      content: inputMessage.trim()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await axios.post('/chat', {
        query: userMessage.content,
        product_name: selectedProduct === 'Tất cả' ? null : selectedProduct
      })

      const { answer, sources } = response.data

      // Xử lý strict mode
      let botReply = answer
      if (strictMode && (!answer || answer.toLowerCase().startsWith('không có'))) {
        botReply = 'Không có thông tin.'
      } else if (sources && sources.length > 0) {
        const sourceText = sources.join('\n')
        botReply = `${answer}\n\n---\n**Nguồn tham khảo:**\n${sourceText}`
      }

      const botMessage = {
        role: 'assistant',
        content: botReply,
        sources: sources // Lưu sources để hiển thị PDF viewer
      }

      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        role: 'assistant',
        content: '❌ Có lỗi xảy ra khi kết nối với server. Vui lòng thử lại.'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  // Parse source để lấy file, page, quote
  const parseSource = (sourceText) => {
    // Format: - **file.pdf** (trang 5)\n  > *"quote text"*
    const fileMatch = sourceText.match(/\*\*([^*]+)\*\*/)
    const pageMatch = sourceText.match(/trang (\d+)/)
    const quoteMatch = sourceText.match(/>\s*\*"([^"]+)"\*/)
    
    return {
      file: fileMatch ? fileMatch[1] : null,
      page: pageMatch ? parseInt(pageMatch[1]) : null,
      quote: quoteMatch ? quoteMatch[1] : null
    }
  }

  const handleSourceClick = (sourceText) => {
    const parsed = parseSource(sourceText)
    if (parsed.file && parsed.quote) {
      // Map file name to actual path
      const pdfPath = `/docs/${parsed.file}`
      setPdfData({
        url: pdfPath,
        searchTexts: [parsed.quote],
        page: parsed.page
      })
      setShowPdfViewer(true)
    }
  }

  return (
    <div className={`chat-layout ${showPdfViewer ? 'split-view' : ''}`}>
      <div className="chat-container">
        <div className="chat-header">
          <div className="header-title">
            <Bot className="header-icon" />
            <h1>Vertiv Chatbot</h1>
          </div>
          <p className="header-subtitle">Hỗ trợ kỹ thuật Vertiv</p>
        </div>

      <div className="chat-controls">
        <div className="control-group">
          <label htmlFor="product-select">Chọn sản phẩm:</label>
          <select
            id="product-select"
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="product-select"
          >
            {PRODUCTS.map(product => (
              <option key={product} value={product}>
                {product}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={strictMode}
              onChange={(e) => setStrictMode(e.target.checked)}
            />
            <span>Strict mode (chỉ trả lời nếu có dữ liệu thật)</span>
          </label>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <Bot size={48} className="empty-icon" />
            <p>Xin chào! Tôi có thể giúp gì cho bạn về sản phẩm Vertiv?</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-icon">
              {message.role === 'user' ? (
                <User size={20} />
              ) : (
                <Bot size={20} />
              )}
            </div>
            <div className="message-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
              
              {/* Nút xem PDF nếu có sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="source-actions">
                  {message.sources.map((source, idx) => {
                    const parsed = parseSource(source)
                    if (parsed.file && parsed.quote) {
                      return (
                        <button
                          key={idx}
                          className="view-pdf-btn"
                          onClick={() => handleSourceClick(source)}
                        >
                          <FileText size={16} />
                          <span>Xem {parsed.file} (trang {parsed.page})</span>
                        </button>
                      )
                    }
                    return null
                  })}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <div className="message-icon">
              <Bot size={20} />
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Nhập câu hỏi của bạn..."
          className="chat-input"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!inputMessage.trim() || isLoading}
        >
          <Send size={20} />
        </button>
      </form>
      </div>

      {/* PDF Viewer Panel - hiển thị bên cạnh khi showPdfViewer = true */}
      {showPdfViewer && (
        <div className="pdf-viewer-panel">
          <div className="pdf-viewer-header">
            <h3>📄 Tài liệu tham khảo</h3>
            <button 
              className="close-pdf-btn"
              onClick={() => setShowPdfViewer(false)}
            >
              ✕
            </button>
          </div>
          <PdfViewer
            fileUrl={pdfData.url}
            searchTexts={pdfData.searchTexts}
            targetPage={pdfData.page}
            onTextFound={(found) => {
              if (found) {
                console.log('Text found and highlighted')
              } else {
                console.log('Text not found in PDF')
              }
            }}
          />
        </div>
      )}
    </div>
  )
}

export default ChatInterface
