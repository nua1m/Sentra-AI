import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false)
    return (
        <button
            className="btn-cyber"
            style={{ fontSize: '0.6rem', padding: '0.2rem 0.5rem', position: 'absolute', top: '0.4rem', right: '0.4rem' }}
            onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        >
            {copied ? 'ACK' : 'CPY'}
        </button>
    )
}

function FixCard({ fix, index }) {
    const cmds = fix.commands?.filter(c => c.trim()).join('\n') || ''
    return (
        <div className="glass-panel" style={{ padding: '0.8rem', marginBottom: '0.8rem', borderLeft: `3px solid var(--${getSeverityColor(fix.severity)})` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <div style={{ fontFamily: 'Orbitron', fontSize: '0.7rem', color: `var(--${getSeverityColor(fix.severity)})` }}>
                    FIX_SEQ_0{index + 1}
                </div>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{fix.severity.toUpperCase()} PRIORITY</div>
            </div>
            <div style={{ fontSize: '0.8rem', marginBottom: '0.5rem' }}>{fix.description}</div>
            {cmds && (
                <div style={{ background: '#000', padding: '0.5rem', fontFamily: 'JetBrains Mono', fontSize: '0.7rem', color: 'var(--safe-green)', position: 'relative' }}>
                    <CopyButton text={cmds} />
                    {cmds}
                </div>
            )}
        </div>
    )
}

function getSeverityColor(sev) {
    switch (sev?.toLowerCase()) {
        case 'critical': return 'alert-red'
        case 'high': return 'alert-red'
        case 'medium': return 'warn-yellow'
        case 'low': return 'safe-green'
        default: return 'primary-cyan'
    }
}

function TypewriterText({ text, speed = 5 }) {
    const [displayed, setDisplayed] = useState('')

    useEffect(() => {
        let i = 0
        setDisplayed('')
        const interval = setInterval(() => {
            setDisplayed(text.slice(0, i))
            i += speed
            if (i > text.length) clearInterval(interval)
        }, 10)
        return () => clearInterval(interval)
    }, [text, speed])

    return (
        <div style={{ fontFamily: 'JetBrains Mono', fontSize: '0.85rem', lineHeight: '1.6', color: 'var(--text-dim)' }}>
            <ReactMarkdown
                components={{
                    strong: ({ node, ...props }) => <span style={{ color: 'var(--primary-cyan)', fontWeight: 'bold' }} {...props} />,
                    h1: ({ node, ...props }) => <h1 style={{ fontFamily: 'Orbitron', color: 'var(--primary-cyan)', fontSize: '1.2rem', margin: '1rem 0', borderBottom: '1px solid var(--border-glass)' }} {...props} />,
                    h2: ({ node, ...props }) => <h2 style={{ fontFamily: 'Orbitron', color: 'var(--text-bright)', fontSize: '1rem', margin: '0.8rem 0' }} {...props} />,
                    h3: ({ node, ...props }) => <h3 style={{ color: 'var(--safe-green)', fontSize: '0.9rem', margin: '0.5rem 0' }} {...props} />,
                    ul: ({ node, ...props }) => <ul style={{ paddingLeft: '1rem', listStyle: 'none' }} {...props} />,
                    li: ({ node, ...props }) => <li style={{ marginBottom: '0.3rem', position: 'relative' }} {...props}><span style={{ color: 'var(--primary-cyan)', marginRight: '0.5rem' }}>{'>'}</span>{props.children}</li>,
                    p: ({ node, ...props }) => <p style={{ marginBottom: '0.8rem' }} {...props} />,
                }}
            >
                {displayed}
            </ReactMarkdown>
            <span className="typing-cursor">_</span>
        </div>
    )
}

export default function ResultCard({ scan, fixes, onExport }) {
    const [tab, setTab] = useState('analysis')
    const findings = fixes?.fixes?.findings || []

    return (
        <div className="glass-panel text-glow" style={{ marginTop: '0.5rem', borderRadius: '4px' }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)' }}>
                {['analysis', 'fixes', 'nmap', 'nikto'].map(t => (
                    <div
                        key={t}
                        className={`log-tab ${tab === t ? 'active' : ''}`}
                        onClick={() => setTab(t)}
                    >
                        {t.toUpperCase()}
                    </div>
                ))}
                <div style={{ flex: 1 }} />
                <button onClick={onExport} className="log-tab" style={{ color: 'var(--primary-cyan)' }}>
                    📄 EXPORT_LOG
                </button>
            </div>

            <div className="log-content">
                {tab === 'analysis' && (
                    <TypewriterText text={scan.analysis} />
                )}
                {tab === 'fixes' && (
                    <div>
                        {findings.map((f, i) => <FixCard key={i} fix={f} index={i} />)}
                        {fixes?.fixes?.ai_recommendations && (
                            <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--primary-cyan)', color: 'var(--primary-cyan)', fontSize: '0.8rem' }}>
                                <div style={{ fontFamily: 'Orbitron', marginBottom: '0.5rem' }}>// TACTICAL RECOMMENDATIONS</div>
                                {fixes.fixes.ai_recommendations}
                            </div>
                        )}
                    </div>
                )}
                {(tab === 'nmap' || tab === 'nikto') && (
                    <div style={{ fontSize: '0.7rem', whiteSpace: 'pre-wrap', color: 'var(--text-dim)' }}>
                        {scan[tab] || 'NO DATA CAPTURED'}
                    </div>
                )}
            </div>
        </div>
    )
}
