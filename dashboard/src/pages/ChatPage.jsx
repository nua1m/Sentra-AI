import { useState, useEffect, useRef } from 'react'
import ScanViz from '../components/ScanViz'
import ResultCard from '../components/ResultCard'
import { fetchScan, fetchFixes, exportPdf, startScan } from '../api'

// TACTICAL LOADER (Updated Text)
function TacticalLoader() {
    const [text, setText] = useState('Establishing Uplink...')
    useEffect(() => {
        const steps = [
            'Establishing Secure Uplink...',
            'Verifying Personnel ID...',
            'Awaiting Neural Response...',
            'Synchronizing Data Stream...',
            'Processing Request...'
        ]
        let i = 0
        const interval = setInterval(() => { setText(steps[i++ % steps.length]) }, 800)
        return () => clearInterval(interval)
    }, [])
    return (
        <div className="msg-row">
            <div className="msg-avatar ai">S</div>
            <div className="msg-bubble ai" style={{ opacity: 0.8 }}>
                <div className="font-mono text-cyan-500 text-xs mb-1">SENTRA_CORE // LINK_ACTIVE</div>
                <div style={{ fontFamily: 'JetBrains Mono', fontSize: '0.8rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="scan-spinner" style={{ width: '12px', height: '12px', borderColor: 'var(--text-dim)', borderTopColor: 'var(--primary-cyan)' }}></span>
                    {text}
                </div>
            </div>
        </div>
    )
}

const WELCOME_MSG = {
    id: 'welcome',
    role: 'ai',
    text: "Initializing Sentra.AI Protocol v2.5...\n\nSystems Online. Neural Engine Active.\n\nAwaiting operator command. Say **\"Scan localhost\"** to begin target acquisition.",
}

const SUGGESTIONS = [
    { text: 'Scan localhost' },
    { text: 'Explain port scanning' },
    { text: 'Secure SSH service' },
]

export default function ChatPage({ activeScanId, onScanStarted, onScanComplete }) {
    const [messages, setMessages] = useState([WELCOME_MSG])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const bottomRef = useRef(null)

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, sending])

    // Load past scan from sidebar
    useEffect(() => {
        if (!activeScanId) return

        // Check if we already have this scan in history to avoid duplication
        const existing = messages.find(m => m.scanId === activeScanId)
        if (existing) return

        const load = async () => {
            try {
                const data = await fetchScan(activeScanId)
                if (data.status === 'complete') {
                    try {
                        const fixes = await fetchFixes(activeScanId)
                        setMessages(prev => [
                            ...prev,
                            { id: `req-${Date.now()}`, role: 'user', text: `View Scan: ${data.target}` },
                            { id: `res-${activeScanId}`, role: 'ai', type: 'scan_result', scanId: activeScanId, data, fixes }
                        ])
                    } catch { }
                }
            } catch { }
        }
        load()
    }, [activeScanId])

    // Polling Effect for ACTIVE scans
    useEffect(() => {
        // Find any message that is 'scan_running'
        const activeScanMsg = messages.find(m => m.type === 'scan_running')
        if (!activeScanMsg) return

        const interval = setInterval(async () => {
            try {
                const data = await fetchScan(activeScanMsg.scanId)

                // Update the message state
                setMessages(prev => prev.map(m => {
                    if (m.scanId === activeScanMsg.scanId) {

                        // Current stage from backend
                        const serverStage = data.scan_stage || data.status
                        const isComplete = data.status === 'complete'

                        // STAGE ORDER DEFINITION
                        const STAGES = ['nmap_running', 'nmap_done', 'nikto_running', 'nikto_done', 'analyzing', 'generating_fixes', 'complete']

                        // Helper to get index
                        const getStageIdx = (s) => STAGES.indexOf(s)

                        const currentIdx = getStageIdx(m.stage || 'nmap_running')
                        const serverIdx = getStageIdx(serverStage)

                        // If already complete in UI, do nothing
                        if (m.type === 'scan_result') return m

                        // LOGIC: If backend is ahead, only advance ONE step per tick to animate
                        // If backend is complete, we still step through until we hit 'complete'

                        let nextStage = m.stage
                        let nextType = m.type
                        let nextData = m.data
                        let nextFixes = m.fixes

                        if (currentIdx < serverIdx || (isComplete && currentIdx < STAGES.length - 1)) {
                            // Advance one step
                            nextStage = STAGES[currentIdx + 1]
                        } else {
                            // Sync with server if we caught up (or server corresponds to current)
                            nextStage = serverStage
                        }

                        // If we finally hit complete in UI
                        if (nextStage === 'complete' || (isComplete && currentIdx >= STAGES.indexOf('generating_fixes'))) {
                            onScanComplete?.()
                            // Populate data
                            return { ...m, type: 'scan_result', data, fixes: null, stage: 'complete' }
                        }

                        return { ...m, stage: nextStage }
                    }
                    return m
                }))

                // Formatting result if complete (prefetch fixes)
                if (data.status === 'complete') {
                    try {
                        const fixes = await fetchFixes(activeScanMsg.scanId)
                        setMessages(prev => prev.map(m =>
                            m.scanId === activeScanMsg.scanId ? { ...m, fixes } : m
                        ))
                    } catch { }
                }

            } catch { }
        }, 2000) // 2s per step for deliberate, cinematic sequencing

        return () => clearInterval(interval)
    }, [messages])


    async function handleSend(text) {
        const msg = text || input.trim()
        if (!msg || sending) return

        setInput('')
        setMessages(prev => [...prev, { id: Date.now(), role: 'user', text: msg }])
        setSending(true)

        try {
            const res = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            })
            const data = await res.json()

            if (data.type === 'action_required' && data.action === 'start_scan') {
                const scanRes = await startScan(data.target)
                if (scanRes.scan_id) {
                    onScanStarted?.(scanRes.scan_id)
                    setMessages(prev => [...prev, {
                        id: scanRes.scan_id,
                        role: 'ai',
                        type: 'scan_running',
                        scanId: scanRes.scan_id,
                        stage: 'nmap_running',
                        target: data.target
                    }])
                } else {
                    setMessages(prev => [...prev, { role: 'ai', text: `[ERROR] Launch Failed: ${scanRes.detail}` }])
                }
            } else {
                setMessages(prev => [...prev, { role: 'ai', text: data.message || 'No response.' }])
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'ai', text: `[CRITICAL] Connection Lost: ${err.message}` }])
        }
        setSending(false)
    }

    return (
        <div className="chat-window">
            {messages.map((msg, i) => (
                <div key={i} className={`msg-row ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'ai' && <div className="msg-avatar ai">S</div>}

                    <div className={`msg-bubble ${msg.role}`} style={{ width: msg.type ? '100%' : 'auto' }}>
                        <div className="font-mono text-xs mb-1" style={{ color: msg.role === 'ai' ? 'var(--primary-cyan)' : 'var(--text-muted)' }}>
                            {msg.role === 'ai' ? 'SENTRA_CORE' : 'OPERATOR'}
                        </div>

                        {/* Text Content */}
                        {msg.text && <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{formatMessage(msg.text)}</div>}

                        {/* Widgets */}
                        {(msg.type === 'scan_running' || msg.type === 'scan_result') && (
                            <ScanViz scanStage={msg.type === 'scan_result' ? 'complete' : msg.stage} />
                        )}

                        {msg.type === 'scan_result' && (
                            <ResultCard
                                scan={msg.data}
                                fixes={msg.fixes}
                                onExport={() => exportPdf(msg.scanId)}
                            />
                        )}
                    </div>

                    {msg.role === 'user' && <div className="msg-avatar user">O</div>}
                </div>
            ))}

            {sending && <TacticalLoader />}

            {messages.length === 1 && (
                <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem', justifyContent: 'center' }}>
                    {SUGGESTIONS.map((s, i) => (
                        <button key={i} className="btn-cyber" onClick={() => handleSend(s.text)}>
                            {`> ${s.text}`}
                        </button>
                    ))}
                </div>
            )}

            <div ref={bottomRef} style={{ height: '100px' }} />

            <div className="input-bar-wrapper">
                <div className="cmd-input-group">
                    <span className="cmd-prompt">root@sentra:~$</span>
                    <input
                        className="cmd-input"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder="Enter command..."
                        disabled={sending}
                        autoFocus
                    />
                    {sending && <span className="typing-cursor">_</span>}
                </div>
            </div>
        </div>
    )
}

function formatMessage(text) {
    if (!text) return text
    const parts = text.split(/(\*\*.*?\*\*)/g)
    return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i} style={{ color: 'var(--primary-cyan)' }}>{part.slice(2, -2)}</strong>
        }
        return part
    })
}
