import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ChatPage from './pages/ChatPage'
import { fetchHealth, fetchScans, removeScan } from './api'
import { ThemeProvider } from './components/theme-provider'
import './index.css'

export default function App() {
  const [health, setHealth] = useState(null)
  const [scans, setScans] = useState([])
  const [activeScanId, setActiveScanId] = useState(null)
  const [scanStage, setScanStage] = useState(null)
  const [chatSessionId, setChatSessionId] = useState(Date.now())

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

  const handleDeleteScan = async (id) => {
    await removeScan(id);
    if (activeScanId === id) {
      setActiveScanId(null);
      setChatSessionId(Date.now());
    }
    refreshScans();
  }

  const handleNewScan = () => {
    setActiveScanId(null);
    setChatSessionId(Date.now());
  }

  return (
    <ThemeProvider defaultTheme="dark" storageKey="sentra-ui-theme">
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar
          health={health}
          scans={scans}
          activeScanId={activeScanId}
          onSelectScan={(id) => { setActiveScanId(id); setChatSessionId(Date.now()); }}
          onNewScan={handleNewScan}
          onDeleteScan={handleDeleteScan}
        />

        <main className="flex-1 flex flex-col overflow-hidden bg-background">
          <TopBar scanStage={scanStage} activeScanId={activeScanId} scans={scans} />
          <ChatPage
            key={chatSessionId}
            activeScanId={activeScanId}
            onScanStarted={(id) => { setActiveScanId(id); refreshScans() }}
            onScanComplete={refreshScans}
            onStageChange={setScanStage}
          />
        </main>
      </div>
    </ThemeProvider>
  )
}
