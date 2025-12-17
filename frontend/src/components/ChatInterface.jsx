import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, FileText, Menu, ChevronDown, ChevronUp, Layers } from 'lucide-react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import PdfViewer from './PdfViewer'
import FileSelectionTree from './FileSelectionTree'
import './ChatInterface.css'

function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')

  // Selected files from Tree
  const [selectedFiles, setSelectedFiles] = useState([])
  const [showSidebar, setShowSidebar] = useState(true) // Toggle sidebar on mobile/desktop

  const [strictMode, setStrictMode] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showPdfViewer, setShowPdfViewer] = useState(false)
  const [pdfData, setPdfData] = useState({ url: '', searchTexts: [], page: null })
  
  // State để quản lý việc hiển thị chunks cho mỗi message
  const [expandedChunks, setExpandedChunks] = useState({})
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
      // Backend expects list of strings (filenames) or null for all
      const fileNames = selectedFiles.length > 0 ? selectedFiles : null

      const response = await axios.post('/chat', {
        query: userMessage.content,
        file_names: fileNames
      })

      const { answer, sources, chunks } = response.data

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
        sources: sources, // Lưu sources để hiển thị PDF viewer
        chunks: chunks || [] // Lưu chunks để hiển thị khi user click
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

  // Toggle hiển thị chunks cho message cụ thể
  const toggleChunks = (messageIndex) => {
    setExpandedChunks(prev => ({
      ...prev,
      [messageIndex]: !prev[messageIndex]
    }))
  }

  return (
    <div className={`chat-layout ${showPdfViewer ? 'split-view' : ''}`}>
      {/* Sidebar for File Selection */}
      <div className={`chat-sidebar ${showSidebar ? 'open' : 'closed'}`}>
        <FileSelectionTree onSelectionChange={setSelectedFiles} />
      </div>

      <div className="chat-container">
        <div className="chat-header">
          <div className="header-left">
            <button
              className="toggle-sidebar-btn"
              onClick={() => setShowSidebar(!showSidebar)}
              title={showSidebar ? "Ẩn danh sách file" : "Hiện danh sách file"}
            >
              <Menu size={20} />
            </button>
            <div className="header-title">
              <Bot className="header-icon" />
              <h1>Vertiv Chatbot</h1>
            </div>
          </div>
          <div className="header-right">
            <label className="checkbox-label strict-mode-toggle">
              <input
                type="checkbox"
                checked={strictMode}
                onChange={(e) => setStrictMode(e.target.checked)}
              />
              <span>Strict mode</span>
            </label>
          </div>
        </div>

        {/* Selected Files Hint */}
        <div className="selection-hint">
          {selectedFiles.length === 0 ? (
            <span className="hint-all">Đang tìm kiếm trong <b>TẤT CẢ</b> tài liệu</span>
          ) : (
            <span className="hint-specific">Đang tìm kiếm trong <b>{selectedFiles.length}</b> tài liệu đã chọn</span>
          )}
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <Bot size={48} className="empty-icon" />
              <p>Xin chào! Tôi có thể giúp gì cho bạn về sản phẩm Vertiv?</p>
              <p className="sub-text">
                {selectedFiles.length === 0
                  ? "Tôi sẽ tìm kiếm câu trả lời trong toàn bộ kho dữ liệu."
                  : `Tôi sẽ chỉ tìm kiếm trong ${selectedFiles.length} file bạn đã chọn.`}
              </p>
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

                {/* Nút xem chunks đã sử dụng */}
                {message.chunks && message.chunks.length > 0 && (
                  <div className="chunks-section">
                    <button
                      className="view-chunks-btn"
                      onClick={() => toggleChunks(index)}
                    >
                      <Layers size={16} />
                      <span>Xem {message.chunks.length} chunks đã sử dụng</span>
                      {expandedChunks[index] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    
                    {expandedChunks[index] && (
                      <div className="chunks-list">
                        {message.chunks.map((chunk, chunkIdx) => (
                          <div key={chunkIdx} className="chunk-item">
                            <div className="chunk-header">
                              <span className="chunk-number">Chunk {chunkIdx + 1}</span>
                              <span className="chunk-source">
                                📄 {chunk.source || 'unknown.pdf'}
                                {chunk.page_range && chunk.page_range.length > 0 && (
                                  <span className="chunk-page"> (trang {chunk.page_range[0]})</span>
                                )}
                              </span>
                              {chunk.score && (
                                <span className="chunk-score">Score: {chunk.score.toFixed(3)}</span>
                              )}
                            </div>
                            <div className="chunk-content">
                              {chunk.text.length > 500 
                                ? chunk.text.substring(0, 500) + '...' 
                                : chunk.text}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
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
