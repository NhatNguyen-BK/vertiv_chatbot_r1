import { useState, useEffect, useRef } from 'react'
import { Upload, FolderPlus, Plus, Check, AlertCircle, X, FileText, Trash2, Loader2 } from 'lucide-react'
import axios from 'axios'
import './UploadManager.css'

function UploadManager() {
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedProductLine, setSelectedProductLine] = useState('')
  const [selectedProduct, setSelectedProduct] = useState('')
  
  // Trạng thái hiển thị form tạo mới
  const [showNewCategoryForm, setShowNewCategoryForm] = useState(false)
  const [showNewProductLineForm, setShowNewProductLineForm] = useState(false)
  const [showNewProductForm, setShowNewProductForm] = useState(false)
  
  // Form inputs cho tạo mới
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newProductLineName, setNewProductLineName] = useState('')
  const [newProductName, setNewProductName] = useState('')
  
  // Multi-file state
  const [files, setFiles] = useState([]) // Array of objects: { file, id, status: 'pending'|'uploading'|'success'|'error', message }
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef(null)

  // Load hierarchy từ API
  useEffect(() => {
    loadHierarchy()
  }, [])

  const loadHierarchy = async () => {
    try {
      const response = await axios.get('/product-hierarchy')
      setCategories(response.data)
    } catch (error) {
      console.error('Error loading hierarchy:', error)
    }
  }

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    const newFiles = selectedFiles
      .filter(file => file.type === 'application/pdf')
      .map(file => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        status: 'pending',
        message: ''
      }))
    
    if (selectedFiles.length !== newFiles.length) {
      alert('Một số file không phải là PDF và đã bị bỏ qua.')
    }

    setFiles(prev => [...prev, ...newFiles])
    
    // Reset input to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (id) => {
    if (isUploading) return
    setFiles(prev => prev.filter(f => f.id !== id))
  }

  const clearFiles = () => {
    if (isUploading) return
    setFiles([])
  }

  // Hàm tạo ID từ name
  const generateId = (name) => {
    return name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Bỏ dấu tiếng Việt
      .replace(/đ/g, 'd')
      .replace(/[^a-z0-9\s]/g, '') // Chỉ giữ chữ và số
      .trim()
      .replace(/\s+/g, '_') // Thay space bằng underscore
  }

  const handleUpload = async () => {
    // Validate selection
    const categoryName = selectedCategory 
      ? categories.find(c => c.id === selectedCategory)?.name 
      : newCategoryName
    const categoryId = selectedCategory || generateId(newCategoryName)
    
    const productLineName = selectedProductLine
      ? categories.find(c => c.id === categoryId)?.product_lines.find(pl => pl.id === selectedProductLine)?.name
      : newProductLineName
    const productLineId = selectedProductLine || generateId(newProductLineName)
    
    const productName = selectedProduct
      ? categories.find(c => c.id === categoryId)?.product_lines
          .find(pl => pl.id === productLineId)?.products.find(p => p.id === selectedProduct)?.name
      : newProductName
    const productId = selectedProduct || generateId(newProductName)

    if (!categoryId || !categoryName) {
      alert('Vui lòng chọn hoặc tạo Category')
      return
    }
    if (!productLineId || !productLineName) {
      alert('Vui lòng chọn hoặc tạo Product Line')
      return
    }
    if (!productId || !productName) {
      alert('Vui lòng chọn hoặc tạo Product')
      return
    }
    
    const pendingFiles = files.filter(f => f.status === 'pending' || f.status === 'error')
    if (pendingFiles.length === 0) {
      alert('Không có file nào để upload')
      return
    }

    setIsUploading(true)

    // Process files sequentially
    for (const fileObj of files) {
      if (fileObj.status === 'success') continue

      // Update status to uploading
      setFiles(prev => prev.map(f => 
        f.id === fileObj.id ? { ...f, status: 'uploading' } : f
      ))

      try {
        const formData = new FormData()
        formData.append('file', fileObj.file)
        formData.append('category_id', categoryId)
        formData.append('category_name', categoryName)
        formData.append('product_line_id', productLineId)
        formData.append('product_line_name', productLineName)
        formData.append('product_id', productId)
        formData.append('product_name', productName)

        await axios.post('/upload-file', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })

        // Update status to success
        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { ...f, status: 'success', message: 'Upload thành công' } : f
        ))
      } catch (error) {
        console.error('Upload error:', error)
        // Update status to error
        setFiles(prev => prev.map(f => 
          f.id === fileObj.id ? { 
            ...f, 
            status: 'error', 
            message: error.response?.data?.detail || error.message 
          } : f
        ))
      }
    }

    setIsUploading(false)
    
    // Reset forms if needed and reload hierarchy
    if (showNewCategoryForm || showNewProductLineForm || showNewProductForm) {
      setShowNewCategoryForm(false)
      setShowNewProductLineForm(false)
      setShowNewProductForm(false)
      setNewCategoryName('')
      setNewProductLineName('')
      setNewProductName('')
      await loadHierarchy()
    }
  }

  const getProductLines = () => {
    if (!selectedCategory) return []
    const category = categories.find(c => c.id === selectedCategory)
    return category?.product_lines || []
  }

  const getProducts = () => {
    if (!selectedCategory || !selectedProductLine) return []
    const category = categories.find(c => c.id === selectedCategory)
    const productLine = category?.product_lines.find(pl => pl.id === selectedProductLine)
    return productLine?.products || []
  }

  return (
    <div className="upload-manager">
      <div className="upload-header">
        <Upload className="header-icon" />
        <div>
          <h2>Quản lý tài liệu</h2>
          <p>Upload file PDF và tạo cấu trúc sản phẩm</p>
        </div>
      </div>

      <div className="upload-content">
        {/* Sidebar: Structure Selection */}
        <div className="upload-sidebar">
          {/* Category Selection */}
          <div className="form-section">
            <h3>
              <FolderPlus size={18} />
              Category
            </h3>
            
            {!showNewCategoryForm ? (
              <>
                <div className="form-group">
                  <select
                    value={selectedCategory}
                    onChange={(e) => {
                      setSelectedCategory(e.target.value)
                      setSelectedProductLine('')
                      setSelectedProduct('')
                    }}
                  >
                    <option value="">-- Chọn category --</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  className="create-new-button"
                  onClick={() => setShowNewCategoryForm(true)}
                >
                  <Plus size={16} />
                  Tạo Category mới
                </button>
              </>
            ) : (
              <div className="new-form">
                <div className="new-form-header">
                  <span>Tạo Category mới</span>
                  <button
                    type="button"
                    className="close-form-button"
                    onClick={() => {
                      setShowNewCategoryForm(false)
                      setNewCategoryName('')
                    }}
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="form-group">
                  <label>Tên Category:</label>
                  <input
                    type="text"
                    value={newCategoryName}
                    onChange={(e) => setNewCategoryName(e.target.value)}
                    placeholder="vd: DC Power"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Product Line Selection */}
          <div className="form-section">
            <h3>
              <Plus size={18} />
              Product Line
            </h3>
            
            {!showNewProductLineForm ? (
              <>
                <div className="form-group">
                  <select
                    value={selectedProductLine}
                    onChange={(e) => {
                      setSelectedProductLine(e.target.value)
                      setSelectedProduct('')
                    }}
                    disabled={!selectedCategory && !newCategoryName}
                  >
                    <option value="">-- Chọn product line --</option>
                    {getProductLines().map(pl => (
                      <option key={pl.id} value={pl.id}>
                        {pl.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  className="create-new-button"
                  onClick={() => setShowNewProductLineForm(true)}
                  disabled={!selectedCategory && !newCategoryName}
                >
                  <Plus size={16} />
                  Tạo Product Line mới
                </button>
              </>
            ) : (
              <div className="new-form">
                <div className="new-form-header">
                  <span>Tạo Product Line mới</span>
                  <button
                    type="button"
                    className="close-form-button"
                    onClick={() => {
                      setShowNewProductLineForm(false)
                      setNewProductLineName('')
                    }}
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="form-group">
                  <label>Tên Product Line:</label>
                  <input
                    type="text"
                    value={newProductLineName}
                    onChange={(e) => setNewProductLineName(e.target.value)}
                    placeholder="vd: Netsure 731"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Product Selection */}
          <div className="form-section">
            <h3>
              <Check size={18} />
              Product
            </h3>
            
            {!showNewProductForm ? (
              <>
                <div className="form-group">
                  <select
                    value={selectedProduct}
                    onChange={(e) => setSelectedProduct(e.target.value)}
                    disabled={!selectedProductLine && !newProductLineName}
                  >
                    <option value="">-- Chọn product --</option>
                    {getProducts().map(p => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  className="create-new-button"
                  onClick={() => setShowNewProductForm(true)}
                  disabled={!selectedProductLine && !newProductLineName}
                >
                  <Plus size={16} />
                  Tạo Product mới
                </button>
              </>
            ) : (
              <div className="new-form">
                <div className="new-form-header">
                  <span>Tạo Product mới</span>
                  <button
                    type="button"
                    className="close-form-button"
                    onClick={() => {
                      setShowNewProductForm(false)
                      setNewProductName('')
                    }}
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="form-group">
                  <label>Tên Product:</label>
                  <input
                    type="text"
                    value={newProductName}
                    onChange={(e) => setNewProductName(e.target.value)}
                    placeholder="vd: A41"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Area: File Upload */}
        <div className="upload-main">
          <div 
            className="upload-area"
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf"
              multiple
              style={{ display: 'none' }}
            />
            <div className="upload-placeholder">
              <Upload className="upload-icon" />
              <div>
                <span className="browse-text">Click để chọn file</span> hoặc kéo thả file vào đây
              </div>
              <p>Hỗ trợ định dạng PDF</p>
            </div>
          </div>

          {files.length > 0 && (
            <>
              <div className="file-list">
                <div className="file-list-header">
                  <h3>Danh sách file ({files.length})</h3>
                  <button 
                    className="clear-button"
                    onClick={clearFiles}
                    disabled={isUploading}
                  >
                    Xóa tất cả
                  </button>
                </div>
                
                {files.map(fileObj => (
                  <div key={fileObj.id} className={`upload-item ${fileObj.status}`}>
                    <FileText className="file-type-icon" size={24} />
                    <div className="file-details">
                      <span className="file-name">{fileObj.file.name}</span>
                      <span className="file-size">{(fileObj.file.size / 1024 / 1024).toFixed(2)} MB</span>
                      {fileObj.message && (
                        <div className={`upload-status status-${fileObj.status}`}>
                          {fileObj.status === 'error' && <AlertCircle size={14} />}
                          {fileObj.status === 'success' && <Check size={14} />}
                          <span>{fileObj.message}</span>
                        </div>
                      )}
                    </div>
                    
                    {fileObj.status === 'uploading' ? (
                      <Loader2 className="animate-spin" size={20} color="#2563eb" />
                    ) : (
                      <button
                        className="remove-file-button"
                        onClick={() => removeFile(fileObj.id)}
                        disabled={isUploading}
                      >
                        <X size={20} />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="upload-actions">
                <button
                  className="upload-button"
                  onClick={handleUpload}
                  disabled={isUploading || files.length === 0}
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="animate-spin" size={20} />
                      Đang upload...
                    </>
                  ) : (
                    <>
                      <Upload size={20} />
                      Upload {files.filter(f => f.status !== 'success').length} file
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default UploadManager
