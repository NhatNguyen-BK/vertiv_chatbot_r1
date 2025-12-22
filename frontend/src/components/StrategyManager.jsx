import { useState, useEffect } from 'react'
import { Plus, Trash2, Play, Save, ChevronDown, ChevronUp, Settings } from 'lucide-react'
import axios from 'axios'
import './StrategyManager.css'

function StrategyManager() {
    const [strategies, setStrategies] = useState([])
    const [loading, setLoading] = useState(false)

    // Form create
    const [newStrategy, setNewStrategy] = useState({
        name: '',
        description: '',
        initial_top_k: 10,
        rerank_top_k: 5,
        score_threshold: 0.0
    })

    // Test section
    const [testQuery, setTestQuery] = useState('')
    const [testConfig, setTestConfig] = useState({
        initial_top_k: 10,
        rerank_top_k: 5,
        score_threshold: 0.0
    })
    const [testLoading, setTestLoading] = useState(false)
    const [testResults, setTestResults] = useState(null)

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
                ...newStrategy,
                score_threshold: newStrategy.score_threshold || null
            }

            await axios.post('/strategies', payload)

            // Reset form & reload list
            setNewStrategy({
                name: '',
                description: '',
                initial_top_k: 10,
                rerank_top_k: 5,
                score_threshold: 0.0
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
            const res = await axios.post('/strategies/test', {
                query: testQuery,
                initial_top_k: testConfig.initial_top_k,
                rerank_top_k: testConfig.rerank_top_k,
                score_threshold: testConfig.score_threshold || null
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
                                    <label>Initial Top K (Dense/Sparse):</label>
                                    <input
                                        type="number"
                                        value={newStrategy.initial_top_k}
                                        onChange={e => setNewStrategy({ ...newStrategy, initial_top_k: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="form-group half">
                                    <label>Rerank Top K:</label>
                                    <input
                                        type="number"
                                        value={newStrategy.rerank_top_k}
                                        onChange={e => setNewStrategy({ ...newStrategy, rerank_top_k: parseInt(e.target.value) })}
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>Score Threshold (Optional):</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={newStrategy.score_threshold}
                                    onChange={e => setNewStrategy({ ...newStrategy, score_threshold: parseFloat(e.target.value) })}
                                    placeholder="Ví dụ: 0.5"
                                />
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
                                                        <div>Initial Top K: <b>{s.initial_top_k}</b></div>
                                                        <div>Rerank Top K: <b>{s.rerank_top_k}</b></div>
                                                        <div>Threshold: <b>{s.score_threshold ?? 'None'}</b></div>
                                                    </div>
                                                    <button className="btn-small btn-test-copy" onClick={() => {
                                                        setTestConfig({
                                                            initial_top_k: s.initial_top_k,
                                                            rerank_top_k: s.rerank_top_k,
                                                            score_threshold: s.score_threshold || 0
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
                                <label>Init K</label>
                                <input
                                    type="number"
                                    value={testConfig.initial_top_k}
                                    onChange={e => setTestConfig({ ...testConfig, initial_top_k: parseInt(e.target.value) })}
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
                            <div className="form-group small">
                                <label>Threshold</label>
                                <input
                                    type="number" step="0.01"
                                    value={testConfig.score_threshold}
                                    onChange={e => setTestConfig({ ...testConfig, score_threshold: parseFloat(e.target.value) })}
                                />
                            </div>
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
                                <h4>Kết quả ({testResults.chunks.length} chunks)</h4>
                                <div className="results-list">
                                    {testResults.chunks.map((chunk, idx) => (
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
                                    ))}
                                </div>
                                {testResults.chunks.length === 0 && <p>Không tìm thấy chunks nào.</p>}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

export default StrategyManager
