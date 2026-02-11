import { useState } from 'react'

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false)
    return (
        <button
            className={`copy-btn ${copied ? 'copied' : ''}`}
            onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        >
            {copied ? '✓ Copied' : 'Copy'}
        </button>
    )
}

function FixCard({ fix, index }) {
    const cmds = fix.commands?.filter(c => c.trim()).join('\n') || ''
    return (
        <div className={`fix-card ${fix.severity?.toLowerCase()}`}>
            <div className="fix-header">
                <span className="fix-title">Fix #{index + 1}: {fix.description}</span>
                <span className={`badge badge-${fix.severity?.toLowerCase()}`}>{fix.severity}</span>
            </div>
            <div className="fix-source">
                Source: {fix.port ? `Nmap — Port ${fix.port}` : `Nikto — ${fix.finding || 'Web scan'}`}
            </div>
            {cmds && (
                <div className="fix-commands">
                    <CopyButton text={cmds} />
                    {cmds}
                </div>
            )}
        </div>
    )
}

export default function ResultCard({ scan, fixes, onExport }) {
    const [tab, setTab] = useState('analysis')
    const [exporting, setExporting] = useState(false)
    const [exportMsg, setExportMsg] = useState('')
    const findings = fixes?.fixes?.findings || []

    const handleExport = async () => {
        setExporting(true)
        try {
            const result = await onExport()
            setExportMsg(result?.path ? `✅ ${result.path}` : '❌ Failed')
        } catch { setExportMsg('❌ Export failed') }
        setExporting(false)
        setTimeout(() => setExportMsg(''), 5000)
    }

    return (
        <div className="result-card">
            <div className="result-tabs">
                {[
                    { id: 'analysis', label: '🧠 Analysis' },
                    { id: 'fixes', label: `🛡️ Fixes (${findings.length})` },
                    { id: 'nmap', label: '📡 Nmap' },
                    { id: 'nikto', label: '🌐 Nikto' },
                ].map(t => (
                    <button
                        key={t.id}
                        className={`result-tab ${tab === t.id ? 'active' : ''}`}
                        onClick={() => setTab(t.id)}
                    >
                        {t.label}
                    </button>
                ))}
                <div style={{ flex: 1 }} />
                <div style={{ padding: '0.4rem 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {exportMsg && <span style={{ fontSize: '0.7rem', color: 'var(--accent-green)' }}>{exportMsg}</span>}
                    <button className="btn btn-outline" onClick={handleExport} disabled={exporting}>
                        {exporting ? '...' : '📄 PDF'}
                    </button>
                </div>
            </div>

            <div className="result-body">
                {tab === 'analysis' && (
                    <div className="analysis-text">{scan.analysis || 'No analysis available.'}</div>
                )}
                {tab === 'fixes' && (
                    <div>
                        {findings.length === 0 ? (
                            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                                No actionable findings
                            </div>
                        ) : (
                            findings.map((f, i) => <FixCard key={i} fix={f} index={i} />)
                        )}
                        {fixes?.fixes?.ai_recommendations && (
                            <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-primary)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                                <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--accent-cyan)' }}>💡 AI Recommendations</div>
                                <div className="analysis-text">{fixes.fixes.ai_recommendations}</div>
                            </div>
                        )}
                    </div>
                )}
                {tab === 'nmap' && <div className="raw-output">{scan.nmap || 'No Nmap data.'}</div>}
                {tab === 'nikto' && <div className="raw-output">{scan.nikto || 'No Nikto data.'}</div>}
            </div>
        </div>
    )
}
