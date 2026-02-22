import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ChatPage from './pages/ChatPage'
import { fetchHealth, fetchScans } from './api'
import './index.css'

export default function App() {
  const [health, setHealth] = useState(null)
  const [scans, setScans] = useState([])
  const [activeScanId, setActiveScanId] = useState(null)

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null))
    fetchScans().then(setScans).catch(() => { })

    const interval = setInterval(() => {
      fetchHealth().then(setHealth).catch(() => { })
      fetchScans().then(setScans).catch(() => { })
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const refreshScans = () => fetchScans().then(setScans).catch(() => { })

  return (
    <div className="app-container">
      <Sidebar
        health={health}
        scans={scans}
        activeScanId={activeScanId}
        onSelectScan={setActiveScanId}
        onNewChat={() => setActiveScanId(null)}
      />

      <div className="main-content">
        <TopBar />
        <ChatPage
          activeScanId={activeScanId}
          onScanStarted={(id) => { setActiveScanId(id); refreshScans() }}
          onScanComplete={refreshScans}
        />
      </div>
    </div>
  )
}
