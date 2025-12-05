import { useState, useEffect } from 'react'
import { FolderOpen, File, Trash2, ChevronRight, ChevronDown, AlertCircle, CheckCircle } from 'lucide-react'
import axios from 'axios'
import './FileManager.css'

function FileManager() {
  const [hierarchy, setHierarchy] = useState([])
  const [expandedCategories, setExpandedCategories] = useState(new Set())
  const [expandedProductLines, setExpandedProductLines] = useState(new Set())
  const [expandedProducts, setExpandedProducts] = useState(new Set())
  const [files, setFiles] = useState({}) // { product_id: [files] }
  const [deleteStatus, setDeleteStatus] = useState({ type: '', message: '' })
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    loadHierarchy()
  }, [])

  const loadHierarchy = async () => {
    try {
      const response = await axios.get('/product-hierarchy')
      setHierarchy(response.data)
    } catch (error) {
      console.error('Error loading hierarchy:', error)
      setDeleteStatus({ type: 'error', message: 'Không thể tải danh sách tài liệu' })
    }
  }

  const loadFilesForProduct = async (productId) => {
    if (files[productId]) return // Already loaded
    
    try {
      const response = await axios.get(`/files?product_id=${productId}`)
      setFiles(prev => ({ ...prev, [productId]: response.data }))
    } catch (error) {
      console.error('Error loading files:', error)
    }
  }

  const toggleCategory = (categoryId) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId)
      } else {
        newSet.add(categoryId)
      }
      return newSet
    })
  }

  const toggleProductLine = (productLineId) => {
    setExpandedProductLines(prev => {
      const newSet = new Set(prev)
      if (newSet.has(productLineId)) {
        newSet.delete(productLineId)
      } else {
        newSet.add(productLineId)
      }
      return newSet
    })
  }

  const toggleProduct = (productId) => {
    setExpandedProducts(prev => {
      const newSet = new Set(prev)
      if (newSet.has(productId)) {
        newSet.delete(productId)
      } else {
        newSet.add(productId)
        loadFilesForProduct(productId)
      }
      return newSet
    })
  }

  const handleDeleteFile = async (fileId, fileName, e) => {
    e.stopPropagation() // Prevent expanding/collapsing
    
    if (!confirm(`Bạn có chắc muốn xóa file "${fileName}"?`)) {
      return
    }

    setIsDeleting(true)
    setDeleteStatus({ type: '', message: '' })

    try {
      await axios.delete(`/files/${fileId}`)
      
      // Reload files for all expanded products
      const reloadPromises = Array.from(expandedProducts).map(async (productId) => {
        const response = await axios.get(`/files?product_id=${productId}`)
        return { productId, files: response.data }
      })
      
      const results = await Promise.all(reloadPromises)
      const newFiles = { ...files }
      results.forEach(({ productId, files: productFiles }) => {
        newFiles[productId] = productFiles
      })
      setFiles(newFiles)
      
      setDeleteStatus({ 
        type: 'success', 
        message: `✅ Đã xóa file "${fileName}" thành công` 
      })
      
      setTimeout(() => {
        setDeleteStatus({ type: '', message: '' })
      }, 3000)
      
    } catch (error) {
      console.error('Error deleting file:', error)
      setDeleteStatus({ 
        type: 'error', 
        message: `❌ Lỗi khi xóa file: ${error.response?.data?.detail || error.message}` 
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDeleteProduct = async (productId, productName, e) => {
    e.stopPropagation()
    
    const productFiles = files[productId] || []
    const fileCount = productFiles.length
    
    if (!confirm(
      `Bạn có chắc muốn xóa product "${productName}"?\n` +
      `Điều này sẽ xóa ${fileCount} file(s) bên trong.`
    )) {
      return
    }

    setIsDeleting(true)
    setDeleteStatus({ type: '', message: '' })

    try {
      await axios.delete(`/products/${productId}`)
      
      // Reload hierarchy
      await loadHierarchy()
      
      // Clear files cache for this product
      const newFiles = { ...files }
      delete newFiles[productId]
      setFiles(newFiles)
      
      setDeleteStatus({ 
        type: 'success', 
        message: `✅ Đã xóa product "${productName}" và ${fileCount} file(s)` 
      })
      
      setTimeout(() => {
        setDeleteStatus({ type: '', message: '' })
      }, 3000)
      
    } catch (error) {
      console.error('Error deleting product:', error)
      setDeleteStatus({ 
        type: 'error', 
        message: `❌ Lỗi khi xóa product: ${error.response?.data?.detail || error.message}` 
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDeleteProductLine = async (productLineId, productLineName, productCount, e) => {
    e.stopPropagation()
    
    if (!confirm(
      `Bạn có chắc muốn xóa product line "${productLineName}"?\n` +
      `Điều này sẽ xóa ${productCount} product(s) và tất cả files bên trong.`
    )) {
      return
    }

    setIsDeleting(true)
    setDeleteStatus({ type: '', message: '' })

    try {
      await axios.delete(`/product-lines/${productLineId}`)
      
      // Reload hierarchy
      await loadHierarchy()
      
      // Clear files cache
      setFiles({})
      
      setDeleteStatus({ 
        type: 'success', 
        message: `✅ Đã xóa product line "${productLineName}" và ${productCount} product(s)` 
      })
      
      setTimeout(() => {
        setDeleteStatus({ type: '', message: '' })
      }, 3000)
      
    } catch (error) {
      console.error('Error deleting product line:', error)
      setDeleteStatus({ 
        type: 'error', 
        message: `❌ Lỗi khi xóa product line: ${error.response?.data?.detail || error.message}` 
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const handleDeleteCategory = async (categoryId, categoryName, productLineCount, e) => {
    e.stopPropagation()
    
    if (!confirm(
      `Bạn có chắc muốn xóa category "${categoryName}"?\n` +
      `Điều này sẽ xóa ${productLineCount} product line(s) và tất cả products/files bên trong.`
    )) {
      return
    }

    setIsDeleting(true)
    setDeleteStatus({ type: '', message: '' })

    try {
      await axios.delete(`/categories/${categoryId}`)
      
      // Reload hierarchy
      await loadHierarchy()
      
      // Clear all caches
      setFiles({})
      setExpandedCategories(new Set())
      setExpandedProductLines(new Set())
      setExpandedProducts(new Set())
      
      setDeleteStatus({ 
        type: 'success', 
        message: `✅ Đã xóa category "${categoryName}" và ${productLineCount} product line(s)` 
      })
      
      setTimeout(() => {
        setDeleteStatus({ type: '', message: '' })
      }, 3000)
      
    } catch (error) {
      console.error('Error deleting category:', error)
      setDeleteStatus({ 
        type: 'error', 
        message: `❌ Lỗi khi xóa category: ${error.response?.data?.detail || error.message}` 
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const getTotalFiles = () => {
    let total = 0
    hierarchy.forEach(cat => {
      cat.product_lines.forEach(pl => {
        pl.products.forEach(p => {
          if (files[p.id]) {
            total += files[p.id].length
          }
        })
      })
    })
    return total
  }

  return (
    <div className="file-manager">
      <div className="file-manager-header">
        <FolderOpen className="header-icon" size={32} />
        <h2>Quản lý tài liệu</h2>
        <p>Xem và quản lý các tài liệu đã upload</p>
      </div>

      {deleteStatus.message && (
        <div className={`status-message ${deleteStatus.type}`}>
          {deleteStatus.type === 'error' && <AlertCircle size={20} />}
          {deleteStatus.type === 'success' && <CheckCircle size={20} />}
          <span>{deleteStatus.message}</span>
        </div>
      )}

      <div className="file-tree">
        {hierarchy.length === 0 ? (
          <div className="empty-state">
            <FolderOpen size={48} className="empty-icon" />
            <p>Chưa có tài liệu nào</p>
            <span>Vui lòng upload tài liệu từ tab "Upload tài liệu"</span>
          </div>
        ) : (
          <>
            {hierarchy.map(category => (
              <div key={category.id} className="tree-item category-item">
                <div 
                  className="tree-header"
                  onClick={() => toggleCategory(category.id)}
                >
                  <div className="tree-title">
                    {expandedCategories.has(category.id) ? (
                      <ChevronDown size={20} />
                    ) : (
                      <ChevronRight size={20} />
                    )}
                    <FolderOpen size={20} className="folder-icon" />
                    <span className="tree-name">{category.name}</span>
                    <span className="tree-count">
                      ({category.product_lines.length} product lines)
                    </span>
                    <button
                      className="delete-button delete-category"
                      onClick={(e) => handleDeleteCategory(category.id, category.name, category.product_lines.length, e)}
                      disabled={isDeleting}
                      title="Xóa category"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {expandedCategories.has(category.id) && (
                  <div className="tree-children">
                    {category.product_lines.map(productLine => (
                      <div key={productLine.id} className="tree-item productline-item">
                        <div 
                          className="tree-header"
                          onClick={() => toggleProductLine(productLine.id)}
                        >
                          <div className="tree-title">
                            {expandedProductLines.has(productLine.id) ? (
                              <ChevronDown size={18} />
                            ) : (
                              <ChevronRight size={18} />
                            )}
                            <FolderOpen size={18} className="folder-icon" />
                            <span className="tree-name">{productLine.name}</span>
                            <span className="tree-count">
                              ({productLine.products.length} products)
                            </span>
                            <button
                              className="delete-button delete-productline"
                              onClick={(e) => handleDeleteProductLine(productLine.id, productLine.name, productLine.products.length, e)}
                              disabled={isDeleting}
                              title="Xóa product line"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </div>

                        {expandedProductLines.has(productLine.id) && (
                          <div className="tree-children">
                            {productLine.products.map(product => {
                              const productFiles = files[product.id] || []
                              return (
                                <div key={product.id} className="tree-item product-item">
                                  <div 
                                    className="tree-header"
                                    onClick={() => toggleProduct(product.id)}
                                  >
                                    <div className="tree-title">
                                      {expandedProducts.has(product.id) ? (
                                        <ChevronDown size={16} />
                                      ) : (
                                        <ChevronRight size={16} />
                                      )}
                                      <FolderOpen size={16} className="folder-icon" />
                                      <span className="tree-name">{product.name}</span>
                                      <span className="tree-count">
                                        ({productFiles.length} files)
                                      </span>
                                      <button
                                        className="delete-button delete-product"
                                        onClick={(e) => handleDeleteProduct(product.id, product.name, e)}
                                        disabled={isDeleting}
                                        title="Xóa product"
                                      >
                                        <Trash2 size={14} />
                                      </button>
                                    </div>
                                  </div>

                                  {expandedProducts.has(product.id) && (
                                    <div className="tree-children files-list">
                                      {productFiles.length === 0 ? (
                                        <div className="no-files">
                                          <File size={16} />
                                          <span>Chưa có file nào</span>
                                        </div>
                                      ) : (
                                        productFiles.map(file => (
                                          <div key={file.id} className="file-item">
                                            <div className="file-info">
                                              <File size={16} className="file-icon" />
                                              <span className="file-name">{file.name}</span>
                                            </div>
                                            <button
                                              className="delete-button delete-file"
                                              onClick={(e) => handleDeleteFile(file.id, file.name, e)}
                                              disabled={isDeleting}
                                              title="Xóa file"
                                            >
                                              <Trash2 size={16} />
                                            </button>
                                          </div>
                                        ))
                                      )}
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

export default FileManager
