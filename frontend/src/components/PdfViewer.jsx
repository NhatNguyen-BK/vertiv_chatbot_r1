import { useState, useEffect, useRef } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import './PdfViewer.css'

// Setup PDF.js worker - sử dụng CDN thay vì local
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`

function PdfViewer({ fileUrl, searchTexts = [], targetPage = null, onTextFound }) {
  const [numPages, setNumPages] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pagesRendered, setPagesRendered] = useState(new Set())
  const containerRef = useRef(null)
  const [containerWidth, setContainerWidth] = useState(0)

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages)
    setLoading(false)
    setError(null)
    setPagesRendered(new Set())
  }

  const onDocumentLoadError = (error) => {
    console.error('Error loading PDF:', error)
    setError(`Không thể tải PDF: ${error.message}`)
    setLoading(false)
  }

  // Tự động cập nhật width theo container
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth - 32)
      }
    }
    updateWidth()
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])

  // Highlight text sau khi page render xong
  useEffect(() => {
    if (searchTexts.length > 0 && pagesRendered.size > 0) {
      const timeoutId = setTimeout(() => {
        highlightSearchTexts()
      }, 500)
      return () => clearTimeout(timeoutId)
    }
  }, [searchTexts, pagesRendered])

  // Scroll to target page
  useEffect(() => {
    if (targetPage && containerRef.current) {
      const timeoutId = setTimeout(() => {
        const pageElement = document.getElementById(`page-${targetPage}`)
        if (pageElement) {
          pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 1000)
      return () => clearTimeout(timeoutId)
    }
  }, [targetPage, numPages])

  // Hàm tách text thành từ + ký tự đặc biệt
  const splitText = (text) => {
    return (
      text.match(/[A-Za-z0-9]+|[^A-Za-z0-9\s]+/g) || []
    ).map((t) => t.trim()).filter((t) => t.length > 0)
  }

  const highlightSearchTexts = () => {
    if (!containerRef.current) return

    const spans = Array.from(
      containerRef.current.querySelectorAll(
        '.react-pdf__Page__textContent span'
      )
    )

    // Reset style
    spans.forEach((span) => {
      span.style.removeProperty('color')
      span.style.removeProperty('background')
      span.style.removeProperty('box-shadow')
      span.style.removeProperty('font-weight')
      span.style.removeProperty('text-shadow')
      span.classList.remove('highlighted-text')
    })

    if (!spans.length) return

    // Gom span thành dòng theo tọa độ top
    const lines = []
    spans.forEach((span) => {
      const rect = span.getBoundingClientRect()
      const top = Math.round(rect.top)
      let line = lines.find((l) => Math.abs(l.top - top) < 5)
      if (!line) {
        line = { top, spans: [], text: '' }
        lines.push(line)
      }
      line.spans.push(span)
      line.text += ' ' + (span.textContent || '')
    })

    // Tách searchTexts thành các word
    const searchWords = searchTexts
      .map((t) => splitText(t))
      .flat()

    console.log('Search words:', searchWords)

    // Tìm dòng có nhiều từ khớp nhất
    let bestLine = null
    let maxMatches = 0

    lines.forEach((line) => {
      const lineWords = splitText(line.text)
      let count = 0

      searchWords.forEach((word) => {
        if (lineWords.includes(word)) count++
      })

      console.log('Line:', line.text, '=> matches:', count)

      if (count > maxMatches) {
        maxMatches = count
        bestLine = line
      }
    })

    if (bestLine && maxMatches > 0) {
      console.log('✅ Best line:', bestLine.text, 'matches:', maxMatches)
      
      // Highlight tất cả span trong dòng
      bestLine.spans.forEach((span) => {
        span.style.background = '#FFA50080'
        span.style.color = '#000'
        span.style.fontWeight = 'bold'
        span.classList.add('highlighted-text')
      })

      // Scroll đến dòng
      const spanRect = bestLine.spans[0].getBoundingClientRect()
      const containerRect = containerRef.current.getBoundingClientRect()
      const currentScrollTop = containerRef.current.scrollTop
      const spanTop = spanRect.top - containerRect.top + currentScrollTop
      const targetScrollTop = spanTop - 200
      
      containerRef.current.scrollTo({
        top: Math.max(0, targetScrollTop),
        behavior: 'smooth',
      })

      onTextFound?.(true)
    } else {
      console.log('❌ Không tìm thấy dòng nào khớp:', searchTexts)
      onTextFound?.(false)
    }
  }

  const onPageRenderSuccess = (pageNumber) => {
    setPagesRendered(prev => new Set([...prev, pageNumber]))
  }

  // Render tất cả các trang
  const renderAllPages = () => {
    if (!numPages) return null

    const pages = []
    for (let i = 1; i <= numPages; i++) {
      pages.push(
        <div key={i} className="pdf-page-container" id={`page-${i}`}>
          <div className="pdf-page-number">
            Trang {i} / {numPages}
          </div>
          <Page 
            pageNumber={i} 
            width={containerWidth > 0 ? containerWidth : undefined}
            loading={<div className="pdf-page-loading">Đang tải trang {i}...</div>}
            error={<div className="pdf-page-error">Không thể tải trang {i}</div>}
            onRenderSuccess={() => onPageRenderSuccess(i)}
          />
        </div>
      )
    }
    return pages
  }

  return (
    <div className="pdf-viewer-container">
      <div 
        ref={containerRef}
        className="pdf-viewer-content"
      >
        {loading && !error && (
          <div className="pdf-loading">
            <div className="pdf-spinner"></div>
            <p>Đang tải PDF...</p>
          </div>
        )}

        {error && (
          <div className="pdf-error">
            <p className="pdf-error-title">Lỗi:</p>
            <p>{error}</p>
          </div>
        )}

        {!error && (
          <Document
            file={fileUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={<div className="pdf-loading-doc">Đang tải PDF...</div>}
            error={<div className="pdf-error-doc">Không thể tải PDF</div>}
          >
            {renderAllPages()}
          </Document>
        )}
      </div>
    </div>
  )
}

export default PdfViewer
