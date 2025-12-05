import { useState, useEffect } from 'react'
import { FolderOpen, File, ChevronRight, ChevronDown, CheckSquare, Square, MinusSquare } from 'lucide-react'
import axios from 'axios'
import './FileSelectionTree.css'

function FileSelectionTree({ onSelectionChange }) {
    const [hierarchy, setHierarchy] = useState([])
    const [expandedCategories, setExpandedCategories] = useState(new Set())
    const [expandedProductLines, setExpandedProductLines] = useState(new Set())
    const [expandedProducts, setExpandedProducts] = useState(new Set())
    const [files, setFiles] = useState({}) // { product_id: [files] }

    // Selection state
    const [selectedFiles, setSelectedFiles] = useState(new Set()) // Set of filenames
    const [isAllSelected, setIsAllSelected] = useState(false) // If true, implies "Search All" (empty selection list sent to backend)

    useEffect(() => {
        loadHierarchy()
    }, [])

    // Notify parent of selection changes
    useEffect(() => {
        if (selectedFiles.size === 0 && !isAllSelected) {
            // If nothing selected, default to all? Or just empty?
            // User requirement: "if nothing selected means search all"
            onSelectionChange([])
        } else {
            onSelectionChange(Array.from(selectedFiles))
        }
    }, [selectedFiles, isAllSelected])

    const loadHierarchy = async () => {
        try {
            const response = await axios.get('/product-hierarchy')
            setHierarchy(response.data)
        } catch (error) {
            console.error('Error loading hierarchy:', error)
        }
    }

    const loadFilesForProduct = async (productId) => {
        if (files[productId]) return files[productId]

        try {
            const response = await axios.get(`/files?product_id=${productId}`)
            const productFiles = response.data
            setFiles(prev => ({ ...prev, [productId]: productFiles }))
            return productFiles
        } catch (error) {
            console.error('Error loading files:', error)
            return []
        }
    }

    const toggleCategory = (categoryId) => {
        setExpandedCategories(prev => {
            const newSet = new Set(prev)
            if (newSet.has(categoryId)) newSet.delete(categoryId)
            else newSet.add(categoryId)
            return newSet
        })
    }

    const toggleProductLine = (productLineId) => {
        setExpandedProductLines(prev => {
            const newSet = new Set(prev)
            if (newSet.has(productLineId)) newSet.delete(productLineId)
            else newSet.add(productLineId)
            return newSet
        })
    }

    const toggleProduct = async (productId) => {
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

    // Selection Logic
    const handleSelectAllToggle = () => {
        if (selectedFiles.size > 0) {
            setSelectedFiles(new Set()) // Clear selection -> implies "Search All"
        }
        // If already empty, it's already "Search All". 
        // Maybe we need a visual indicator for "Search All" vs "Select Specific"
    }

    const handleFileToggle = (fileName) => {
        setSelectedFiles(prev => {
            const newSet = new Set(prev)
            if (newSet.has(fileName)) newSet.delete(fileName)
            else newSet.add(fileName)
            return newSet
        })
    }

    const handleProductSelect = async (productId, e) => {
        e.stopPropagation()
        // Ensure files are loaded
        let productFiles = files[productId]
        if (!productFiles) {
            productFiles = await loadFilesForProduct(productId)
        }

        if (!productFiles || productFiles.length === 0) return

        const allSelected = productFiles.every(f => selectedFiles.has(f.name))

        setSelectedFiles(prev => {
            const newSet = new Set(prev)
            if (allSelected) {
                // Deselect all
                productFiles.forEach(f => newSet.delete(f.name))
            } else {
                // Select all
                productFiles.forEach(f => newSet.add(f.name))
            }
            return newSet
        })
    }

    // Checkbox states
    const getProductCheckboxState = (productId) => {
        const productFiles = files[productId]
        if (!productFiles || productFiles.length === 0) return 'unchecked'

        const selectedCount = productFiles.filter(f => selectedFiles.has(f.name)).length
        if (selectedCount === 0) return 'unchecked'
        if (selectedCount === productFiles.length) return 'checked'
        return 'indeterminate'
    }

    const renderCheckbox = (state, onClick) => {
        return (
            <div className={`tree-checkbox ${state}`} onClick={onClick}>
                {state === 'checked' && <CheckSquare size={16} className="icon-checked" />}
                {state === 'indeterminate' && <MinusSquare size={16} className="icon-indeterminate" />}
                {state === 'unchecked' && <Square size={16} className="icon-unchecked" />}
            </div>
        )
    }

    return (
        <div className="file-selection-tree">
            <div className="tree-header-main">
                <h3>Chọn tài liệu</h3>
                <button
                    className={`select-all-btn ${selectedFiles.size === 0 ? 'active' : ''}`}
                    onClick={handleSelectAllToggle}
                >
                    {selectedFiles.size === 0 ? 'Đang chọn tất cả' : 'Chọn tất cả'}
                </button>
            </div>

            <div className="tree-content">
                {hierarchy.map(category => (
                    <div key={category.id} className="tree-item category-item">
                        <div className="tree-row">
                            <span className="expand-icon" onClick={() => toggleCategory(category.id)}>
                                {expandedCategories.has(category.id) ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                            </span>
                            <span className="item-label" onClick={() => toggleCategory(category.id)}>
                                <FolderOpen size={18} className="folder-icon" />
                                {category.name}
                            </span>
                        </div>

                        {expandedCategories.has(category.id) && (
                            <div className="tree-children">
                                {category.product_lines.map(productLine => (
                                    <div key={productLine.id} className="tree-item productline-item">
                                        <div className="tree-row">
                                            <span className="expand-icon" onClick={() => toggleProductLine(productLine.id)}>
                                                {expandedProductLines.has(productLine.id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                            </span>
                                            <span className="item-label" onClick={() => toggleProductLine(productLine.id)}>
                                                <FolderOpen size={16} className="folder-icon" />
                                                {productLine.name}
                                            </span>
                                        </div>

                                        {expandedProductLines.has(productLine.id) && (
                                            <div className="tree-children">
                                                {productLine.products.map(product => {
                                                    const checkboxState = getProductCheckboxState(product.id)
                                                    return (
                                                        <div key={product.id} className="tree-item product-item">
                                                            <div className="tree-row">
                                                                <span className="expand-icon" onClick={() => toggleProduct(product.id)}>
                                                                    {expandedProducts.has(product.id) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                                                </span>
                                                                {renderCheckbox(checkboxState, (e) => handleProductSelect(product.id, e))}
                                                                <span className="item-label" onClick={() => toggleProduct(product.id)}>
                                                                    {product.name}
                                                                </span>
                                                            </div>

                                                            {expandedProducts.has(product.id) && (
                                                                <div className="tree-children files-list">
                                                                    {files[product.id]?.map(file => (
                                                                        <div key={file.id} className="file-item">
                                                                            {renderCheckbox(
                                                                                selectedFiles.has(file.name) ? 'checked' : 'unchecked',
                                                                                () => handleFileToggle(file.name)
                                                                            )}
                                                                            <span className="file-name" title={file.name}>{file.name}</span>
                                                                        </div>
                                                                    ))}
                                                                    {(!files[product.id] || files[product.id].length === 0) && (
                                                                        <div className="no-files">Không có file</div>
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
            </div>
        </div>
    )
}

export default FileSelectionTree
