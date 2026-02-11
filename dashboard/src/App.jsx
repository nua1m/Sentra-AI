import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
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
      fetchHealth().then(setHealth).catch(() => setHealth(null))
      fetchScans().then(setScans).catch(() => { })
    }, 8000)
    return () => clearInterval(interval)
  }, [])

  const refreshScans = () => fetchScans().then(setScans).catch(() => { })

  return (
    <div className="app-layout">
      <Sidebar
        health={health}
        scans={scans}
        activeScanId={activeScanId}
        onSelectScan={setActiveScanId}
        onNewChat={() => setActiveScanId(null)}
      />
      <ChatPage
        activeScanId={activeScanId}
        onScanStarted={(id) => { setActiveScanId(id); refreshScans() }}
        onScanComplete={refreshScans}
      />
    </div>
  )
}
