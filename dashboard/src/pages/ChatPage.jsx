import { useState, useEffect, useRef } from 'react'
import ScanViz from '../components/ScanViz'
import ResultCard from '../components/ResultCard'
import AgentTerminal from '../components/AgentTerminal'
import AgentConsole from '../components/AgentConsole'
import { Button } from "@/components/ui/button"
import { fetchScan, fetchFixes, exportPdf, startScan, executeShell } from '../api'

// TACTICAL LOADER
function TacticalLoader({ text = "Processing..." }) {
    return (
        <div className="flex gap-4 mb-8">
            <div className="w-10 h-10 rounded-full bg-slate-50 dark:bg-zinc-900 border border-slate-200 dark:border-slate-800 flex items-center justify-center text-emerald-500 shrink-0 shadow-sm">
                <span className="material-symbols-outlined text-lg">smart_toy</span>
            </div>
            <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm max-w-[680px] w-full flex items-center gap-3">
                <span className="material-symbols-outlined text-emerald-500 animate-spin" style={{ animationDuration: '3s' }}>sync</span>
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
                        if (m.type === 'scan_result') return m

                        const serverStage = data.scan_stage || data.status
                        const isComplete = data.status === 'complete'
                        const toolsUsed = data.tools_used || m.toolsUsed || ['nmap']

                        if (isComplete) {
                            onScanComplete?.()
                            return { ...m, type: 'scan_result', data, fixes: null, stage: 'complete', toolsUsed }
                        }

                        return { ...m, stage: serverStage, toolsUsed }
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
        setSending("Processing...")

        try {
            // [!] AGENT ZERO INTEGRATION OVERRIDE
            if (msg.startsWith("/agent0")) {
                const query = msg.replace("/agent0", "").trim()
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    role: 'ai',
                    type: 'agent0_stream',
                    output: '*Initializing AgentZero Engine...*\n',
                    text: `Running AgentZero Task: ${query}`
                }])
                return handleAgentZero(Date.now() + 1, query)
            }

            // Find the most recent completed scan for context
            const lastScan = messages.slice().reverse().find(m => m.scanId && m.type === 'scan_result')
            const body = { message: msg }
            if (lastScan?.scanId) body.scan_id = lastScan.scanId

            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })

            if (!res.body) throw new Error("ReadableStream not supported in this browser.")

            const reader = res.body.getReader()
            const decoder = new TextDecoder('utf-8')
            let done = false
            let partialBuffer = ''

            while (!done) {
                const { value, done: doneReading } = await reader.read()
                done = doneReading
                if (value) {
                    partialBuffer += decoder.decode(value, { stream: true })

                    const chunks = partialBuffer.split('\n\n')
                    partialBuffer = chunks.pop() || '' // Keep the incomplete chunk

                    for (const chunk of chunks) {
                        const eventMatch = chunk.match(/event:\s*(.*)/)
                        const dataMatch = chunk.match(/data:\s*(.*)/)

                        if (eventMatch && dataMatch) {
                            const eventType = eventMatch[1].trim()
                            const dataPayload = JSON.parse(dataMatch[1].trim())

                            if (eventType === 'status') {
                                setSending(dataPayload) // Updates the dynamic TacticalLoader!
                            } else if (eventType === 'result') {
                                const data = dataPayload

                                if (data.type === 'scan_request') {
                                    setMessages(prev => [...prev, {
                                        id: Date.now(),
                                        role: 'ai',
                                        type: 'scan_request',
                                        target: data.target,
                                        requested_tools: data.requested_tools,
                                        text: data.message
                                    }])
                                } else if (data.type === 'action_required' && data.action === 'execute_shell') {
                                    setMessages(prev => [...prev, {
                                        id: Date.now(),
                                        role: 'ai',
                                        type: 'shell_request',
                                        command: data.command,
                                        text: data.message
                                    }])
                                } else if (data.type === 'action_required' && data.action === 'execute_attack') {
                                    setMessages(prev => [...prev, {
                                        id: Date.now(),
                                        role: 'ai',
                                        type: 'attack_request',
                                        target: data.target,
                                        text: data.message
                                    }])
                                } else if (data.type === 'setup_request') {
                                    setMessages(prev => [...prev, {
                                        id: Date.now(),
                                        role: 'ai',
                                        type: 'setup_request',
                                        target: data.target,
                                        credentials: data.credentials,
                                        text: "I am ready to connect and audit this target. Please authorize."
                                    }])
                                } else {
                                    setMessages(prev => [...prev, { role: 'ai', text: data.message || 'No response.' }])
                                }
                            }
                        }
                    }
                }
            }
        } catch (err) {
            setMessages(prev => [...prev, { role: 'ai', text: `[CRITICAL] Connection Lost: ${err.message}` }])
        }
        setSending(false)
    }

    async function handleAgentZero(msgId, query) {
        setSending(false)
        let localOutput = '*Initializing AgentZero Engine...*\n';

        try {
            const res = await fetch('/api/agent0/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: query })
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                if (value) {
                    const chunkText = decoder.decode(value, { stream: true });
                    const events = chunkText.split('\n\n');
                    for (const ev of events) {
                        const dataMatch = ev.match(/data:\s*(.*)/);
                        if (dataMatch) {
                            try {
                                const parsed = JSON.parse(dataMatch[1].trim());
                                if (parsed.type === 'log' || parsed.type === 'error' || parsed.type === 'status') {
                                    // Append newline for readability
                                    localOutput += parsed.message + '\n';
                                    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: localOutput } : m));
                                }
                            } catch (e) {
                                // Ignore unparseable chunks
                            }
                        }
                    }
                }
            }
        } catch (err) {
            localOutput += `\n[CRITICAL ERROR] Failed to run AgentZero: ${err.message}`;
            setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: localOutput } : m));
        }
    }

    async function handleReconTeam(msgId, target) {
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: '' } : m));
        try {
            const res = await fetch('/api/recon/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;
            let localOutput = '';

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                if (value) {
                    const chunkText = decoder.decode(value, { stream: true });
                    const events = chunkText.split('\n\n');
                    for (const ev of events) {
                        if (ev.includes("event: complete")) {
                            const lines = ev.split('\n');
                            for (let line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const data = JSON.parse(line.substring(6));
                                        if (data.type === 'scan_result') {
                                            setMessages(prev => [...prev, {
                                                id: Date.now(),
                                                role: 'ai',
                                                type: 'scan_result',
                                                data: data.data,
                                                fixes: data.fixes,
                                                scanId: data.scanId
                                            }]);
                                        }
                                    } catch (e) { }
                                }
                            }
                        } else if (ev.includes("event: terminal")) {
                            const lines = ev.split('\n');
                            for (let line of lines) {
                                if (line.startsWith('data: ')) {
                                    try {
                                        const parsed = JSON.parse(line.substring(6));
                                        if (parsed.message) {
                                            localOutput += parsed.message + '\n';
                                        }
                                    } catch (e) { }
                                }
                            }
                            setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: localOutput } : m));
                        }
                    }
                }
            }
        } catch (err) {
            setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: localOutput + `\n\n[ERROR] Connection Lost: ${err.message}` } : m));
        }
    }

    async function handleSetupTeam(msgId, target, credentials) {
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: '' } : m));
        try {
            const body = { target };
            // Simple credential parser: if user said "root / password", we send it. Otherwise setup_agent will ask.
            if (credentials && credentials.includes('/')) {
                const parts = credentials.split('/');
                body.username = parts[0].trim();
                body.password = parts[1].trim();
            } else if (credentials) {
                // assume it's just a password
                body.password = credentials.trim();
            }

            const res = await fetch('/api/setup/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (!res.body) throw new Error("ReadableStream not supported");

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;
            let partialBuffer = '';

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                if (value) {
                    partialBuffer += decoder.decode(value, { stream: true });
                    const chunks = partialBuffer.split('\n\n');
                    partialBuffer = chunks.pop() || '';

                    for (const chunk of chunks) {
                        const eventMatch = chunk.match(/event:\s*(.*)/);
                        const dataMatch = chunk.match(/data:\s*(.*)/);

                        if (eventMatch && dataMatch) {
                            const eventType = eventMatch[1].trim();
                            const dataPayload = JSON.parse(dataMatch[1].trim());

                            if (eventType === 'terminal') {
                                const parsed = typeof dataPayload === 'string' ? JSON.parse(dataPayload) : dataPayload;
                                setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: (m.output || '') + parsed.message + '\n' } : m));
                            } else if (eventType === 'done' || eventType === 'error') {
                                setSending(false);
                            }
                        }
                    }
                }
            }
        } catch (err) {
            setMessages(prev => prev.map(m => m.id === msgId ? { ...m, output: `[CRITICAL ERROR] ${err.message}` } : m));
        }
    }

    async function handlePurpleTeam(msgId, target) {
        setMessages(prev => prev.map(m => m.id === msgId ? { ...m, redOutput: '', blueOutput: '' } : m));
        try {
            const res = await fetch('/api/attack/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });

            if (!res.body) throw new Error("ReadableStream not supported");

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;
            let partialBuffer = '';

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                if (value) {
                    partialBuffer += decoder.decode(value, { stream: true });
                    const chunks = partialBuffer.split('\n\n');
                    partialBuffer = chunks.pop() || '';

                    for (const chunk of chunks) {
                        const eventMatch = chunk.match(/event:\s*(.*)/);
                        const dataMatch = chunk.match(/data:\s*(.*)/);

                        if (eventMatch && dataMatch) {
                            const eventType = eventMatch[1].trim();
                            const dataPayload = JSON.parse(dataMatch[1].trim());

                            if (eventType === 'status') {
                                setSending(dataPayload);
                            } else if (eventType === 'terminal') {
                                const parsed = typeof dataPayload === 'string' ? JSON.parse(dataPayload) : dataPayload;
                                if (parsed.type === 'RED') {
                                    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, redOutput: (m.redOutput || '') + parsed.message + '\n' } : m));
                                } else if (parsed.type === 'BLUE') {
                                    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, blueOutput: (m.blueOutput || '') + parsed.message + '\n' } : m));
                                }
                            } else if (eventType === 'done' || eventType === 'error') {
                                setSending(false);
                            }
                        }
                    }
                }
            }
        } catch (err) {
            setMessages(prev => prev.map(m => m.id === msgId ? { ...m, redOutput: `[CRITICAL ERROR] ${err.message}` } : m));
            setSending(false);
        }
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
                        <div className="max-w-4xl mx-auto w-full p-8 pb-4 space-y-8">
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
                                                <div className="mt-2 w-[680px] max-w-[85vw] space-y-4">
                                                    <ScanViz scanStage={msg.type === 'scan_result' ? 'complete' : msg.stage} toolsUsed={msg.toolsUsed || ['nmap']} />

                                                    {/* Live Terminal Streaming View */}
                                                    {msg.type === 'scan_running' && (
                                                        <AgentTerminal scanId={msg.scanId} />
                                                    )}
                                                </div>
                                            )}

                                            {msg.type === 'shell_request' && (
                                                <div className="mt-2 text-sm bg-slate-900 border border-slate-700 text-slate-300 p-4 rounded-xl max-w-[680px] w-full font-mono flex flex-col gap-4 shadow-sm">
                                                    <div className="flex items-start gap-3">
                                                        <span className="material-symbols-outlined text-emerald-500 mt-0.5 text-lg">terminal</span>
                                                        <div className="flex-1 break-all">
                                                            <span className="text-slate-500 mr-2">$</span>
                                                            <span className="text-emerald-400">{msg.command}</span>
                                                        </div>
                                                    </div>
                                                    {!msg.output ? (
                                                        <Button
                                                            size="sm"
                                                            variant="default"
                                                            className="self-start gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                                                            onClick={async () => {
                                                                try {
                                                                    setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, output: 'Executing...\n' } : m));
                                                                    const res = await executeShell(msg.command);
                                                                    setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, output: res.output } : m));
                                                                } catch (err) {
                                                                    setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, output: `[ERROR] Execution failed: ${err.message}` } : m));
                                                                }
                                                            }}
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                                                            Execute Command
                                                        </Button>
                                                    ) : (
                                                        <div className="bg-black/50 p-3 rounded-lg border border-slate-800 text-slate-400 whitespace-pre-wrap max-h-96 overflow-y-auto mt-2">
                                                            {msg.output}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {msg.type === 'attack_request' && (
                                                <div className="mt-2 text-sm bg-purple-950/30 border border-purple-800/50 text-slate-300 p-4 rounded-xl max-w-full w-full font-sans flex flex-col gap-4 shadow-sm">
                                                    <div className="flex items-start gap-3">
                                                        <span className="material-symbols-outlined text-purple-500 mt-0.5 text-lg">public</span>
                                                        <div className="flex-1 break-all">
                                                            <div className="text-slate-200 font-bold mb-1">Target Assessment</div>
                                                            <span className="text-slate-400 text-sm">Target: </span>
                                                            <span className="text-purple-400 font-bold">{msg.target}</span>
                                                        </div>
                                                    </div>
                                                    {!msg.redOutput && !msg.blueOutput ? (
                                                        <Button
                                                            size="sm"
                                                            variant="destructive"
                                                            className="self-start gap-2 bg-purple-600 hover:bg-purple-700 text-white font-bold"
                                                            onClick={() => handlePurpleTeam(msg.id, msg.target)}
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">swords</span>
                                                            AUTHORIZE PURPLE TEAM
                                                        </Button>
                                                    ) : (
                                                        <div className="grid grid-cols-2 gap-4 h-[550px] w-full mt-2">
                                                            <AgentConsole
                                                                agentType="RED"
                                                                themeColor="red"
                                                                icon="swords"
                                                                status={msg.blueOutput ? "Terminated" : "Attacking"}
                                                                output={msg.redOutput}
                                                            />
                                                            <AgentConsole
                                                                agentType="BLUE"
                                                                themeColor="blue"
                                                                icon="security"
                                                                status={!msg.redOutput ? "Awaiting Breach" : (msg.blueOutput ? "Remediating" : "Analyzing Log...")}
                                                                output={msg.blueOutput}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {msg.type === 'scan_request' && (
                                                <div className="mt-2 text-sm bg-slate-900 border border-blue-500/30 p-4 rounded-xl max-w-[680px] w-full font-sans flex flex-col gap-4 shadow-sm">
                                                    <div className="flex items-start gap-3">
                                                        <div className="flex-1">
                                                            <div className="text-slate-200 font-bold mb-1">Agentic Reconnaissance</div>
                                                            <div className="text-slate-400 text-sm">Deploying the Hybrid Recon Agent (Playwright + MCP) against: <span className="text-blue-400 font-mono">{msg.target}</span></div>
                                                        </div>
                                                    </div>

                                                    {(msg.output === undefined) ? (
                                                        <Button
                                                            size="sm"
                                                            className="self-start gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold"
                                                            onClick={() => handleReconTeam(msg.id, msg.target)}
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">radar</span>
                                                            AUTHORIZE RECON AGENT
                                                        </Button>
                                                    ) : (
                                                        <div className="h-[400px] w-full mt-2">
                                                            <AgentConsole
                                                                agentType="RECON"
                                                                themeColor="blue"
                                                                icon="radar"
                                                                status="Scanning"
                                                                output={msg.output}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {msg.type === 'setup_request' && (
                                                <div className="mt-2 text-sm bg-slate-900 border border-emerald-500/30 p-4 rounded-xl max-w-[680px] w-full font-sans flex flex-col gap-4 shadow-sm">
                                                    <div className="flex items-start gap-3">
                                                        <div className="flex-1">
                                                            <div className="text-slate-200 font-bold mb-1">Connect to Server</div>
                                                            <div className="text-slate-400 text-sm">Please provide SSH credentials for Sentra to securely connect and analyze: <span className="text-emerald-400 font-mono">{msg.target}</span></div>
                                                        </div>
                                                    </div>

                                                    {(msg.output === undefined) ? (
                                                        <Button
                                                            size="sm"
                                                            className="self-start gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                                                            onClick={() => handleSetupTeam(msg.id, msg.target, msg.credentials)}
                                                        >
                                                            <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
                                                            AUTHORIZE SETUP AGENT
                                                        </Button>
                                                    ) : (
                                                        <div className="h-[400px] w-full mt-2">
                                                            <AgentConsole
                                                                agentType="SETUP"
                                                                themeColor="emerald"
                                                                icon="cable"
                                                                status="Analyzing"
                                                                output={msg.output}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {msg.type === 'agent0_stream' && (
                                                <div className="mt-2 text-sm bg-slate-900 border border-emerald-500/50 p-4 rounded-xl max-w-[680px] w-full font-sans flex flex-col gap-4 shadow-sm">
                                                    <div className="flex items-start gap-3">
                                                        <div className="flex-1">
                                                            <div className="text-slate-200 font-bold mb-1">AgentZero Native Engine</div>
                                                            <div className="text-slate-400 text-sm">Running autonomous pipeline directly from the custom offensive security engine.</div>
                                                        </div>
                                                    </div>
                                                    <div className="h-[400px] w-full mt-2">
                                                        <AgentConsole
                                                            agentType="AGENT0"
                                                            themeColor="emerald"
                                                            icon="smart_toy"
                                                            status="Processing"
                                                            output={msg.output}
                                                        />
                                                    </div>
                                                </div>
                                            )}

                                            {msg.type === 'scan_result' && (
                                                <div className="mt-4 w-[680px] max-w-[85vw]">
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

                            {sending && <TacticalLoader text={typeof sending === 'string' ? sending : 'Processing...'} />}
                        </div>
                        <div ref={bottomRef} />
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
