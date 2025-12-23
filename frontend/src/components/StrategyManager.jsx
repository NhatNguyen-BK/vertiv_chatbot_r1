import { useState, useEffect } from 'react'
import { Plus, Trash2, Play, Save, ChevronDown, ChevronUp, Settings } from 'lucide-react'
import axios from 'axios'
import FileSelectionTree from './FileSelectionTree'
import './StrategyManager.css'

function StrategyManager() {
    const [strategies, setStrategies] = useState([])
    const [loading, setLoading] = useState(false)

    // Form create
    const [newStrategy, setNewStrategy] = useState({
        name: '',
        description: '',
        initial_top_k: 10,
        sparse_top_k: 10,
        hybrid_top_k: 10,
        vector_store_query_mode: 'hybrid',
        alpha: 0.5,
        rerank_top_k: 5
    })

    // Test section
    const [testQuery, setTestQuery] = useState('')
    const [testConfig, setTestConfig] = useState({
        initial_top_k: 10,
        sparse_top_k: 10,
        hybrid_top_k: 10,
        vector_store_query_mode: 'hybrid',
        alpha: 0.5,
        rerank_top_k: 5
    })
    const [testLoading, setTestLoading] = useState(false)
    const [testResults, setTestResults] = useState(null)
    const [selectedFiles, setSelectedFiles] = useState([]) // Thêm file selection

    // Expand state for strategy items to show details
    const [expandedId, setExpandedId] = useState(null)

    useEffect(() => {
        fetchStrategies()
    }, [])

    const fetchStrategies = async () => {
        try {
            setLoading(true)
            const res = await axios.get('/strategies')
            if (Array.isArray(res.data)) {
                setStrategies(res.data)
            } else {
                setStrategies([])
            }
        } catch (error) {
            console.error("Failed to fetch strategies", error)
        } finally {
            setLoading(false)
        }
    }

    const handleCreate = async (e) => {
        e.preventDefault()
        try {
            // Validate
            if (!newStrategy.name) return alert("Cần nhập tên chiến lược")

            const payload = {
                ...newStrategy
            }

            await axios.post('/strategies', payload)

            // Reset form & reload list
            setNewStrategy({
                name: '',
                description: '',
                initial_top_k: 10,
                sparse_top_k: 10,
                hybrid_top_k: 10,
                vector_store_query_mode: 'hybrid',
                alpha: 0.5,
                rerank_top_k: 5
            })
            fetchStrategies()
        } catch (error) {
            console.error("Create failed", error)
            alert("Tạo thất bại: " + (error.response?.data?.detail || error.message))
        }
    }

    const handleDelete = async (id) => {
        if (!window.confirm("Bạn chắc chắn muốn xóa chiến lược này?")) return
        try {
            await axios.delete(`/strategies/${id}`)
            fetchStrategies()
        } catch (error) {
            console.error("Delete failed", error)
        }
    }

    const handleTest = async (e) => {
        e.preventDefault()
        if (!testQuery.trim()) return

        try {
            setTestLoading(true)
            const fileNames = selectedFiles.length > 0 ? selectedFiles : null
            const res = await axios.post('/strategies/test', {
                query: testQuery,
                file_names: fileNames,
                initial_top_k: testConfig.initial_top_k,
                sparse_top_k: testConfig.sparse_top_k,
                hybrid_top_k: testConfig.hybrid_top_k,
                vector_store_query_mode: testConfig.vector_store_query_mode,
                alpha: testConfig.alpha,
                rerank_top_k: testConfig.rerank_top_k
            })
            setTestResults(res.data)
        } catch (error) {
            console.error("Test failed", error)
            alert("Test lỗi: " + error.message)
        } finally {
            setTestLoading(false)
        }
    }

    return (
        <div className="strategy-manager">
            <div className="strategy-header">
                <h2><Settings className="icon" /> Quản lý Chiến lược Chunking</h2>
                <p>Tạo và cấu hình các chiến lược tìm kiếm (Retrieval Strategies) để tối ưu kết quả câu trả lời.</p>
            </div>

            <div className="strategy-content">
                {/* Left: List & Create */}
                <div className="strategy-left">
                    <div className="card create-card">
                        <h3>Tạo Chiến Lược Mới</h3>
                        <form onSubmit={handleCreate}>
                            <div className="form-group">
                                <label>Tên chiến lược:</label>
                                <input
                                    type="text"
                                    value={newStrategy.name}
                                    onChange={e => setNewStrategy({ ...newStrategy, name: e.target.value })}
                                    placeholder="Ví dụ: High Precision, Aggressive Search..."
                                />
                            </div>
                            <div className="form-group">
                                <label>Mô tả:</label>
                                <input
                                    type="text"
                                    value={newStrategy.description}
                                    onChange={e => setNewStrategy({ ...newStrategy, description: e.target.value })}
                                    placeholder="Mô tả ngắn gọn..."
                                />
                            </div>
                            <div className="form-row">
                                <div className="form-group half">
                                    <label>Similarity Top K:</label>
                                    <input
                                        type="number"
                                        value={newStrategy.initial_top_k}
                                        onChange={e => setNewStrategy({ ...newStrategy, initial_top_k: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="form-group half">
                                    <label>Sparse Top K:</label>
                                    <input
                                        type="number"
                                        value={newStrategy.sparse_top_k}
                                        onChange={e => setNewStrategy({ ...newStrategy, sparse_top_k: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="form-group half">
                                    <label>Hybrid Top K (Retrieved):</label>
                                    <input
                                        type="number"
                                        value={newStrategy.hybrid_top_k}
                                        onChange={e => setNewStrategy({ ...newStrategy, hybrid_top_k: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="form-group half">
                                    <label>Rerank Top K (Final):</label>
                                    <input
                                        type="number"
                                        value={newStrategy.rerank_top_k}
                                        onChange={e => setNewStrategy({ ...newStrategy, rerank_top_k: parseInt(e.target.value) })}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Query Mode:</label>
                                <select
                                    className="mode-select"
                                    value={newStrategy.vector_store_query_mode}
                                    onChange={e => setNewStrategy({ ...newStrategy, vector_store_query_mode: e.target.value })}
                                >
                                    <option value="default">Default (Dense) - Tìm kiếm ngữ nghĩa thuần túy</option>
                                    <option value="sparse">Sparse (Keyword) - Tìm kiếm theo từ khóa chính xác</option>
                                    <option value="hybrid">Hybrid - Kết hợp Dense + Sparse (cân bằng bởi Alpha)</option>
                                    <option value="text_search">Text Search - Tìm kiếm văn bản thuần</option>
                                    <option value="semantic_hybrid">Semantic Hybrid - Ngữ nghĩa kết hợp hybrid ranking</option>
                                    <option value="svm">SVM - Dùng Support Vector Machine</option>
                                    <option value="logistic_regression">Logistic Regression - Hồi quy logistic</option>
                                    <option value="linear_regression">Linear Regression - Hồi quy tuyến tính</option>
                                    <option value="mmr">MMR - Maximum Marginal Relevance (đa dạng kết quả)</option>
                                </select>
                                <small className="mode-hint">
                                    {newStrategy.vector_store_query_mode === 'default' && '🔍 Phù hợp cho câu hỏi khái niệm, ý nghĩa'}
                                    {newStrategy.vector_store_query_mode === 'sparse' && '🔎 Tốt cho tìm mã sản phẩm, tên chính xác'}
                                    {newStrategy.vector_store_query_mode === 'hybrid' && '⚖️ Cân bằng giữa ngữ nghĩa và từ khóa - khuyên dùng'}
                                    {newStrategy.vector_store_query_mode === 'text_search' && '📝 Tìm kiếm văn bản đơn giản'}
                                    {newStrategy.vector_store_query_mode === 'semantic_hybrid' && '🎯 Kết hợp ngữ nghĩa với xếp hạng lai'}
                                    {newStrategy.vector_store_query_mode === 'mmr' && '🌈 Đa dạng hóa kết quả tìm kiếm'}
                                </small>
                            </div>

                            <div className="form-group">
                                <label>Alpha (0.0 = Sparse | 1.0 = Dense):</label>
                                <input
                                    type="number"
                                    step="0.05" min="0" max="1"
                                    value={newStrategy.alpha}
                                    onChange={e => setNewStrategy({ ...newStrategy, alpha: parseFloat(e.target.value) })}
                                />
                                <small className="mode-hint">⚖️ Alpha = 0.0: Ưu tiên từ khóa | Alpha = 1.0: Ưu tiên ngữ nghĩa</small>
                            </div>

                            <button type="submit" className="btn-primary">
                                <Plus size={16} /> Tạo Mới
                            </button>
                        </form>
                    </div>

                    <div className="card list-card">
                        <h3>Danh sách chiến lược</h3>
                        <div className="strategy-list">
                            {loading ? <p>Loading...</p> : (
                                (!Array.isArray(strategies) || strategies.length === 0) ? <p className="text-muted">Chưa có chiến lược nào.</p> :
                                    strategies.map(s => (
                                        <div key={s.id} className="strategy-item">
                                            <div className="strategy-item-header" onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}>
                                                <div className="strategy-info">
                                                    <strong>{s.name}</strong>
                                                    <span className="strategy-meta">
                                                        K={s.initial_top_k} → R={s.rerank_top_k}
                                                    </span>
                                                </div>
                                                <div className="strategy-actions">
                                                    <button className="btn-icon delete" onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }}>
                                                        <Trash2 size={16} />
                                                    </button>
                                                    {expandedId === s.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                                </div>
                                            </div>
                                            {expandedId === s.id && (
                                                <div className="strategy-details">
                                                    <p>{s.description || "Không có mô tả"}</p>
                                                    <div className="detail-grid">
                                                        <div>Sim K: <b>{s.initial_top_k}</b> | Sparse K: <b>{s.sparse_top_k}</b></div>
                                                        <div>Hybrid K: <b>{s.hybrid_top_k}</b></div>
                                                        <div>Mode: <b>{s.vector_store_query_mode}</b> | Alpha: <b>{s.alpha}</b></div>
                                                        <div>Rerank Top K: <b>{s.rerank_top_k}</b></div>
                                                    </div>
                                                    <button className="btn-small btn-test-copy" onClick={() => {
                                                        setTestConfig({
                                                            initial_top_k: s.initial_top_k,
                                                            sparse_top_k: s.sparse_top_k,
                                                            hybrid_top_k: s.hybrid_top_k,
                                                            vector_store_query_mode: s.vector_store_query_mode,
                                                            alpha: s.alpha,
                                                            rerank_top_k: s.rerank_top_k
                                                        })
                                                    }}>
                                                        Copy to Test
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    ))
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: Test Zone */}
                <div className="strategy-right">
                    <div className="card test-card">
                        <h3>Test Configuration</h3>
                        <div className="test-config-bar">
                            <div className="form-group small">
                                <label>Sim K</label>
                                <input
                                    type="number"
                                    value={testConfig.initial_top_k}
                                    onChange={e => setTestConfig({ ...testConfig, initial_top_k: parseInt(e.target.value) })}
                                />
                            </div>
                            <div className="form-group small">
                                <label>Sparse K</label>
                                <input
                                    type="number"
                                    value={testConfig.sparse_top_k}
                                    onChange={e => setTestConfig({ ...testConfig, sparse_top_k: parseInt(e.target.value) })}
                                />
                            </div>
                            <div className="form-group small">
                                <label>Mode</label>
                                <select
                                    className="mini-select"
                                    value={testConfig.vector_store_query_mode}
                                    onChange={e => setTestConfig({ ...testConfig, vector_store_query_mode: e.target.value })}
                                >
                                    <option value="hybrid">Hybrid</option>
                                    <option value="default">Dense</option>
                                    <option value="sparse">Sparse</option>
                                    <option value="text_search">Text</option>
                                    <option value="semantic_hybrid">Sem. Hybrid</option>
                                    <option value="svm">SVM</option>
                                    <option value="logistic_regression">LogReg</option>
                                    <option value="linear_regression">LinReg</option>
                                    <option value="mmr">MMR</option>
                                </select>
                            </div>
                            <div className="form-group small">
                                <label>Alpha</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="1"
                                    value={testConfig.alpha}
                                    onChange={e => setTestConfig({ ...testConfig, alpha: parseFloat(e.target.value) })}
                                />
                            </div>
                            <div className="form-group small">
                                <label>Rerank K</label>
                                <input
                                    type="number"
                                    value={testConfig.rerank_top_k}
                                    onChange={e => setTestConfig({ ...testConfig, rerank_top_k: parseInt(e.target.value) })}
                                />
                            </div>
                        </div>

                        {/* File Selection */}
                        <div className="file-selection-section">
                            <h4>🗂️ Chọn File để Test</h4>
                            <FileSelectionTree 
                                onSelectionChange={(files) => setSelectedFiles(files)}
                            />
                            {selectedFiles.length > 0 && (
                                <div className="selected-files-info">
                                    Đã chọn: <strong>{selectedFiles.length}</strong> file(s)
                                </div>
                            )}
                        </div>

                        <form onSubmit={handleTest} className="test-form">
                            <input
                                type="text"
                                className="test-input"
                                placeholder="Nhập câu hỏi test..."
                                value={testQuery}
                                onChange={e => setTestQuery(e.target.value)}
                            />
                            <button type="submit" disabled={testLoading} className="btn-test">
                                {testLoading ? 'Running...' : <><Play size={16} /> Test</>}
                            </button>
                        </form>

                        {testResults && (
                            <div className="test-results">
                                <div className="test-answer-section">
                                    <h4>📝 Câu trả lời</h4>
                                    <div className="answer-box">
                                        {testResults.answer || 'Không có câu trả lời'}
                                    </div>
                                </div>
                                
                                <div className="test-chunks-section">
                                    <h4>📚 Chunks Retrieved ({testResults.chunks?.length || 0})</h4>
                                    <div className="results-list">
                                        {testResults.chunks && testResults.chunks.length > 0 ? (
                                            testResults.chunks.map((chunk, idx) => (
                                                <div key={idx} className="result-item">
                                                    <div className="result-header">
                                                        <span className="idx">#{idx + 1}</span>
                                                        <span className="src">{chunk.source}</span>
                                                        <span className="score">{chunk.score ? chunk.score.toFixed(3) : '-'}</span>
                                                    </div>
                                                    <div className="result-text">
                                                        {chunk.text}
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <p>Không tìm thấy chunks nào.</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default StrategyManager
