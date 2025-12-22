import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import UploadManager from './components/UploadManager'
import FileManager from './components/FileManager'
import StrategyManager from './components/StrategyManager'
import { MessageSquare, Upload, FolderOpen, Settings } from 'lucide-react'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('chat') // 'chat' | 'upload' | 'files' | 'strategies'

  return (
    <div className="app">
      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <MessageSquare size={20} />
          <span>Chat</span>
        </button>
        <button
          className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          <Upload size={20} />
          <span>Upload tài liệu</span>
        </button>
        <button
          className={`tab-button ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          <FolderOpen size={20} />
          <span>Quản lý file</span>
        </button>
        <button
          className={`tab-button ${activeTab === 'strategies' ? 'active' : ''}`}
          onClick={() => setActiveTab('strategies')}
        >
          <Settings size={20} />
          <span>Chiến lược</span>
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'upload' && <UploadManager />}
        {activeTab === 'files' && <FileManager />}
        {activeTab === 'strategies' && <StrategyManager />}
      </div>
    </div>
  )
}

export default App
