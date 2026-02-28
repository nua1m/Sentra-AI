import { useState, useEffect, useRef } from 'react'
import ScanViz from '../components/ScanViz'
import ResultCard from '../components/ResultCard'
import AgentTerminal from '../components/AgentTerminal'
import { Button } from "@/components/ui/button"
import { fetchScan, fetchFixes, exportPdf, startScan } from '../api'

// TACTICAL LOADER
function TacticalLoader() {
    const [text, setText] = useState('Establishing Uplink...')
    useEffect(() => {
        const steps = [
            'Analyzing Request...',
            'Connecting to Target...',
            'Initializing Security Suite...',
            'Processing...'
        ]
        let i = 0
        const interval = setInterval(() => { setText(steps[i++ % steps.length]) }, 800)
        return () => clearInterval(interval)
    }, [])
    return (
        <div className="flex gap-4 mb-8">
            <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-white/5 flex items-center justify-center text-primary dark:text-white border border-border-light shrink-0">
                <span className="material-symbols-outlined text-lg">smart_toy</span>
            </div>
            <div className="bg-surface border border-border-light rounded-2xl p-5 shadow-sm max-w-2xl w-full flex items-center gap-3">
                <span className="material-symbols-outlined text-primary dark:text-white animate-spin" style={{ animationDuration: '3s' }}>sync</span>
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{text}</span>
            </div>
        </div>
    )
}

const WELCOME_MSG = {
    id: 'welcome',
    role: 'ai',
    text: "Welcome to Sentra AI Enterprise.\n\nI am your intelligent security assistant. I can automate vulnerability scans, analyze infrastructure risks, and generate remediation scripts.\n\nType **\"Scan localhost\"** or enter a target IP/domain to begin an operation.",
}

const SUGGESTIONS = [
    { text: 'Scan localhost', icon: 'radar' },
    { text: 'Explain port scanning', icon: 'school' },
    { text: 'Secure SSH service', icon: 'security' },
]

export default function ChatPage({ activeScanId, onScanStarted, onScanComplete }) {
    const [messages, setMessages] = useState([WELCOME_MSG])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const bottomRef = useRef(null)

    const prevMessagesLength = useRef(messages.length);

    // Auto-scroll ONLY when a new message arrives, not on every polling update
    useEffect(() => {
        if (messages.length > prevMessagesLength.current || sending) {
            // Delay ensures the DOM has resized
            setTimeout(() => {
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                    const msgEl = document.getElementById(`msg-${lastMsg.id}`);
                    if (msgEl) {
                        // Scroll the new message exactly to the top of the chat view
                        msgEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        return;
                    }
                }
                bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }, 50);
        }
        prevMessagesLength.current = messages.length;
    }, [messages.length, sending])

    // Load past scan from sidebar
    useEffect(() => {
        if (!activeScanId) return

        let mounted = true
        const load = async () => {
            try {
                const data = await fetchScan(activeScanId)
                if (data.status === 'complete') {
                    try {
                        const fixes = await fetchFixes(activeScanId)
                        if (mounted) {
                            setMessages(prev => {
                                // Prevent strict-mode double appending
                                if (prev.find(m => m.scanId === activeScanId)) return prev;

                                return [
                                    ...prev,
                                    { id: `req-${Date.now()}`, role: 'user', text: `View Scan: ${data.target}` },
                                    { id: `res-${activeScanId}`, role: 'ai', type: 'scan_result', scanId: activeScanId, data, fixes }
                                ]
                            })
                        }
                    } catch { }
                }
            } catch { }
        }
        load()
        return () => { mounted = false }
    }, [activeScanId])

    // Polling Effect for ACTIVE scans
    useEffect(() => {
        const activeScanMsg = messages.find(m => m.type === 'scan_running')
        if (!activeScanMsg) return

        const interval = setInterval(async () => {
            try {
                const data = await fetchScan(activeScanMsg.scanId)

                setMessages(prev => prev.map(m => {
                    if (m.scanId === activeScanMsg.scanId) {
                        const serverStage = data.scan_stage || data.status
                        const isComplete = data.status === 'complete'

                        const STAGES = ['nmap_running', 'nmap_done', 'nikto_running', 'nikto_done', 'analyzing', 'generating_fixes', 'complete']
                        const getStageIdx = (s) => STAGES.indexOf(s)

                        const currentIdx = getStageIdx(m.stage || 'nmap_running')
                        const serverIdx = getStageIdx(serverStage)

                        if (m.type === 'scan_result') return m

                        let nextStage = m.stage

                        if (currentIdx < serverIdx || (isComplete && currentIdx < STAGES.length - 1)) {
                            nextStage = STAGES[currentIdx + 1]
                        } else {
                            nextStage = serverStage
                        }

                        if (nextStage === 'complete' || (isComplete && currentIdx >= STAGES.indexOf('generating_fixes'))) {
                            onScanComplete?.()
                            return { ...m, type: 'scan_result', data, fixes: null, stage: 'complete' }
                        }

                        return { ...m, stage: nextStage }
                    }
                    return m
                }))

                if (data.status === 'complete') {
                    try {
                        const fixes = await fetchFixes(activeScanMsg.scanId)
                        setMessages(prev => prev.map(m =>
                            m.scanId === activeScanMsg.scanId ? { ...m, fixes } : m
                        ))
                    } catch { }
                }

            } catch { }
        }, 2000)

        return () => clearInterval(interval)
    }, [messages, onScanComplete])


    async function handleSend(text) {
        const msg = text || input.trim()
        if (!msg || sending) return

        setInput('')
        setMessages(prev => [...prev, { id: Date.now(), role: 'user', text: msg }])
        setSending(true)

        try {
            // Find the most recent completed scan for context
            const lastScan = messages.slice().reverse().find(m => m.scanId && m.type === 'scan_result')
            const body = { message: msg }
            if (lastScan?.scanId) body.scan_id = lastScan.scanId

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
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

    const isDashboardState = messages.length <= 1;

    return (
        <div className="flex-1 flex flex-col h-full bg-background relative overflow-hidden">
            {isDashboardState ? (
                <div className="flex-1 overflow-y-auto p-10 space-y-12">
                    <section className="max-w-5xl mx-auto w-full">
                        <div className="flex items-center gap-3 mb-8">
                            <span className="material-symbols-outlined text-primary text-2xl">auto_awesome</span>
                            <h2 className="text-xl font-bold text-primary tracking-tight">AI Security Assistant</h2>
                        </div>
                        <div className="bg-surface border border-border-light rounded-2xl p-10 shadow-soft flex flex-col">
                            <div className="flex-1 flex flex-col justify-center items-center text-center space-y-5 mb-10">
                                <div className="w-14 h-14 rounded-2xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-primary dark:text-white border border-border-light">
                                    <span className="material-symbols-outlined text-2xl">chat_bubble</span>
                                </div>
                                <div className="space-y-2">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">Intelligent Remediation</h3>
                                    <p className="text-sm text-slate-500 max-w-sm leading-relaxed mx-auto">
                                        Ask anything about your security posture or request automated fix scripts for detected vulnerabilities.
                                    </p>
                                </div>
                            </div>

                            <div className="relative max-w-2xl mx-auto w-full">
                                <form
                                    onSubmit={(e) => { e.preventDefault(); handleSend(input) }}
                                    className="bg-slate-50 dark:bg-black/20 border border-border-light rounded-xl p-2 flex items-center gap-3 shadow-sm focus-within:bg-surface focus-within:ring-2 focus-within:ring-primary/20 transition-all"
                                >
                                    <span className="material-symbols-outlined text-slate-400 ml-3">psychology</span>
                                    <input
                                        type="text"
                                        value={input}
                                        onChange={e => setInput(e.target.value)}
                                        className="bg-transparent border-none focus:ring-0 text-sm flex-1 text-slate-900 dark:text-white placeholder:text-slate-400 outline-none w-full"
                                        placeholder="Type your security query... (e.g. Scan localhost)"
                                        disabled={sending}
                                        autoFocus
                                    />
                                    <div className="flex gap-1 shrink-0">
                                        <Button type="button" variant="ghost" size="icon" className="text-slate-400 hover:text-primary rounded-full transition-colors">
                                            <span className="material-symbols-outlined text-xl">attach_file</span>
                                        </Button>
                                        <Button type="submit" disabled={sending || !input.trim()} className="rounded-lg text-sm font-bold px-6">
                                            {sending ? '...' : 'Send'}
                                        </Button>
                                    </div>
                                </form>
                                <div className="flex flex-wrap gap-2 mt-5 justify-center">
                                    {['Critical Issues', 'Summarize Web', 'Attack Surface'].map(tag => (
                                        <Button
                                            key={tag}
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleSend(`Analyze ${tag.toLowerCase()}`)}
                                            className="text-[11px] font-bold text-slate-500 rounded-full flex items-center gap-1.5 h-8"
                                        >
                                            <span className="material-symbols-outlined text-sm">
                                                {tag === 'Critical Issues' ? 'warning' : tag === 'Summarize Web' ? 'language' : 'shield'}
                                            </span>
                                            {tag}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            ) : (
                <div className="flex-1 flex flex-col relative bg-surface overflow-hidden">
                    <div className="flex-1 overflow-y-auto">
                        <div className="max-w-4xl mx-auto w-full p-8 pb-32 space-y-8">
                            {/* Messages Loop */}
                            {messages.map((msg, i) => {
                                if (msg.role === 'ai' && msg.id === 'welcome') return null; // Hide welcome message in chat view

                                return (
                                    <div key={i} id={`msg-${msg.id}`} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''} pb-4`}>
                                        {/* Avatar */}
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border 
                                    ${msg.role === 'ai'
                                                ? 'bg-slate-50 dark:bg-white/5 text-primary dark:text-white border-border-light'
                                                : 'bg-primary text-primary-foreground border-primary shadow-sm'}`}>
                                            <span className="material-symbols-outlined text-lg">
                                                {msg.role === 'ai' ? 'smart_toy' : 'person'}
                                            </span>
                                        </div>

                                        {/* Bubble */}
                                        <div className={`flex flex-col gap-2 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                            {/* Text Content */}
                                            {msg.text && (
                                                <div className={`p-4 text-sm leading-relaxed shadow-sm
                                            ${msg.role === 'user'
                                                        ? 'bg-primary text-primary-foreground rounded-2xl rounded-tr-sm'
                                                        : 'bg-surface text-slate-700 dark:text-slate-200 border border-border-light rounded-2xl rounded-tl-sm'}`}>
                                                    <div style={{ whiteSpace: 'pre-wrap' }}>{formatMessage(msg.text)}</div>
                                                </div>
                                            )}

                                            {/* Widgets */}
                                            {(msg.type === 'scan_running' || msg.type === 'scan_result') && (
                                                <div className="mt-2 w-full min-w-[320px] space-y-4">
                                                    <ScanViz scanStage={msg.type === 'scan_result' ? 'complete' : msg.stage} />

                                                    {/* Live Terminal Streaming View */}
                                                    {msg.type === 'scan_running' && (
                                                        <AgentTerminal scanId={msg.scanId} />
                                                    )}
                                                </div>
                                            )}

                                            {msg.type === 'scan_result' && (
                                                <div className="mt-4 w-full min-w-[320px]">
                                                    <ResultCard
                                                        scan={msg.data}
                                                        fixes={msg.fixes}
                                                        onExport={() => exportPdf(msg.scanId)}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )
                            })}

                            {sending && <TacticalLoader />}

                            <div ref={bottomRef} className="h-4" />
                        </div>
                    </div>

                    {/* Input Bar pinned to bottom */}
                    <div className="p-6 pb-8 bg-surface shrink-0 border-t border-border-light/50">
                        <div className="max-w-3xl mx-auto w-full">
                            <form
                                onSubmit={(e) => { e.preventDefault(); handleSend(input) }}
                                className="bg-surface border border-border-light rounded-xl p-2 flex items-center gap-3 shadow-md focus-within:ring-2 focus-within:ring-primary/20 transition-all"
                            >
                                <span className="material-symbols-outlined text-slate-400 ml-3">psychology</span>
                                <input
                                    className="bg-transparent border-none focus:ring-0 text-sm flex-1 text-slate-900 dark:text-white placeholder:text-slate-400 outline-none w-full"
                                    value={input}
                                    onChange={e => setInput(e.target.value)}
                                    placeholder="Type your security query or command (e.g., Scan localhost)..."
                                    disabled={sending}
                                    autoFocus
                                />
                                <div className="flex gap-2">
                                    <Button
                                        type="submit"
                                        disabled={sending || !input.trim()}
                                        className="rounded-lg text-sm font-bold px-6 flex items-center gap-2"
                                    >
                                        <span>Send</span>
                                        <span className="material-symbols-outlined text-sm">send</span>
                                    </Button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

function formatMessage(text) {
    if (!text) return text
    const parts = text.split(/(\*\*.*?\*\*)/g)
    return parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={i} className="font-bold text-primary">{part.slice(2, -2)}</strong>
        }
        return part
    })
}
