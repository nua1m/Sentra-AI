import { useState, useEffect, useRef } from 'react'
import ScanViz from '../components/ScanViz'
import ResultCard from '../components/ResultCard'
import { fetchScan, fetchFixes, exportPdf, startScan } from '../api'

const WELCOME_MSG = {
    role: 'ai',
    text: "Welcome to Sentra.AI — your AI cybersecurity assistant.\n\nI can scan targets for vulnerabilities, analyze results, and generate fix commands.\n\nTry saying something like **\"Scan localhost\"** or ask me a cybersecurity question.",
}

const SUGGESTIONS = [
    { icon: '📡', text: 'Scan localhost for open ports' },
    { icon: '🔍', text: 'What is a port scan?' },
    { icon: '🛡️', text: 'How to secure an SSH server?' },
    { icon: '⚡', text: 'Scan 192.168.1.1' },
]

export default function ChatPage({ activeScanId, onScanStarted, onScanComplete }) {
    const [messages, setMessages] = useState([WELCOME_MSG])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const [scanPolling, setScanPolling] = useState(null) // { scanId, stage }
    const [scanResult, setScanResult] = useState(null)   // completed scan data
    const [fixesData, setFixesData] = useState(null)
    const bottomRef = useRef(null)

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, scanPolling, scanResult])

    // Load past scan when clicking sidebar
    useEffect(() => {
        if (!activeScanId) {
            setMessages([WELCOME_MSG])
            setScanResult(null)
            setFixesData(null)
            setScanPolling(null)
            return
        }

        const loadScan = async () => {
            try {
                const data = await fetchScan(activeScanId)
                if (data.status === 'complete') {
                    setMessages([
                        WELCOME_MSG,
                        { role: 'user', text: `Scan ${data.target}` },
                        { role: 'ai', text: `✅ Target **${data.target}** — scan complete.` },
                    ])
                    setScanPolling({ scanId: activeScanId, stage: 'complete' })
                    setScanResult(data)
                    try {
                        const fixes = await fetchFixes(activeScanId)
                        setFixesData(fixes)
                    } catch { }
                }
            } catch { }
        }
        loadScan()
    }, [activeScanId])

    // Polling for active scan
    useEffect(() => {
        if (!scanPolling || scanPolling.stage === 'complete') return

        const interval = setInterval(async () => {
            try {
                const data = await fetchScan(scanPolling.scanId)
                setScanPolling(prev => ({ ...prev, stage: data.scan_stage || data.status }))

                if (data.status === 'complete') {
                    clearInterval(interval)
                    setScanResult(data)
                    addMessage('ai', `✅ Scan of **${data.target}** is complete! Here are the results:`)
                    onScanComplete?.()
                    try {
                        const fixes = await fetchFixes(scanPolling.scanId)
                        setFixesData(fixes)
                    } catch { }
                }
            } catch { }
        }, 1500)

        return () => clearInterval(interval)
    }, [scanPolling?.scanId, scanPolling?.stage])

    function addMessage(role, text) {
        setMessages(prev => [...prev, { role, text }])
    }

    async function handleSend(text) {
        const msg = text || input.trim()
        if (!msg || sending) return

        setInput('')
        addMessage('user', msg)
        setSending(true)

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            })
            const data = await res.json()

            if (data.type === 'action_required' && data.action === 'start_scan') {
                addMessage('ai', `✅ Target **${data.target}** verified. Launching scan...`)

                // Start scan
                const scanRes = await startScan(data.target)
                if (scanRes.scan_id) {
                    onScanStarted?.(scanRes.scan_id)
                    setScanPolling({ scanId: scanRes.scan_id, stage: 'nmap_running' })
                    setScanResult(null)
                    setFixesData(null)
                } else {
                    addMessage('ai', `❌ Failed to start scan: ${scanRes.detail || 'Unknown error'}`)
                }
            } else if (data.type === 'error') {
                addMessage('ai', data.message)
            } else {
                addMessage('ai', data.message || 'No response.')
            }
        } catch (err) {
            addMessage('ai', `❌ Connection error: ${err.message}`)
        }

        setSending(false)
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const showWelcome = messages.length <= 1 && !scanPolling && !scanResult

    return (
        <div className="chat-area">
            <div className="chat-messages">
                {showWelcome ? (
                    <div className="welcome">
                        <div className="welcome-logo">S</div>
                        <h1 className="welcome-title">Sentra.AI</h1>
                        <p className="welcome-text">
                            Your AI-powered cybersecurity assistant. I automate network scanning,
                            vulnerability analysis, and fix generation — all in one place.
                        </p>
                        <div className="welcome-suggestions">
                            {SUGGESTIONS.map((s, i) => (
                                <button key={i} className="suggestion-btn" onClick={() => handleSend(s.text)}>
                                    <div className="suggestion-icon">{s.icon}</div>
                                    <div className="suggestion-text">{s.text}</div>
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, i) => (
                            <div key={i} className="message">
                                <div className={`message-avatar ${msg.role === 'ai' ? 'ai' : 'user'}`}>
                                    {msg.role === 'ai' ? 'S' : 'U'}
                                </div>
                                <div className="message-content">
                                    <div className="message-sender">{msg.role === 'ai' ? 'Sentra.AI' : 'You'}</div>
                                    <div className="message-text">{formatMessage(msg.text)}</div>
                                </div>
                            </div>
                        ))}

                        {/* Live Scan Visualization */}
                        {scanPolling && (
                            <div className="message">
                                <div className="message-avatar ai">S</div>
                                <div className="message-content">
                                    <ScanViz scanStage={scanPolling.stage} />
                                </div>
                            </div>
                        )}

                        {/* Results Card */}
                        {scanResult && scanResult.status === 'complete' && (
                            <div className="message">
                                <div className="message-avatar ai">S</div>
                                <div className="message-content">
                                    <ResultCard
                                        scan={scanResult}
                                        fixes={fixesData}
                                        onExport={() => exportPdf(scanPolling?.scanId)}
                                    />
                                </div>
                            </div>
                        )}
                    </>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="chat-input-area">
                <div className="chat-input-wrapper">
                    <input
                        className="chat-input"
                        placeholder={sending ? 'Processing...' : 'Type a message or "scan <target>"...'}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={sending}
                        autoFocus
                    />
                    <button
                        className="send-btn"
                        onClick={() => handleSend()}
                        disabled={sending || !input.trim()}
                    >
                        <svg className="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13" />
                            <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                    </button>
                </div>
                <div className="input-hint">
                    Sentra.AI uses Nmap + Nikto for scanning. Targets require verification (sentra-verify.txt).
                </div>
            </div>
        </div>
    )
}

// Simple bold formatting for **text**
function formatMessage(text) {
    if (!text) return text
    const parts = text.split(/(\*\*.*?\*\*)/g)
    return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i}>{part.slice(2, -2)}</strong>
        }
        return part
    })
}
