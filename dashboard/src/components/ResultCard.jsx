import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false)
    return (
        <button
            className="absolute top-2 right-2 flex items-center gap-1 bg-slate-100 hover:bg-slate-200 text-slate-600 text-[10px] font-bold px-2 py-1 rounded transition-colors uppercase"
            onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        >
            <span className="material-symbols-outlined text-[12px]">{copied ? 'check' : 'content_copy'}</span>
            {copied ? 'Copied' : 'Copy'}
        </button>
    )
}

function FixCard({ fix, index }) {
    const cmds = fix.commands?.filter(c => c.trim()).join('\n') || ''

    // Soft SaaS colored borders based on severity
    const getBorderColor = (sev) => {
        switch (sev?.toLowerCase()) {
            case 'critical': return 'border-red-500'
            case 'high': return 'border-orange-500'
            case 'medium': return 'border-amber-500'
            case 'low': return 'border-emerald-500'
            default: return 'border-accent-blue'
        }
    }

    const getTextColor = (sev) => {
        switch (sev?.toLowerCase()) {
            case 'critical': return 'text-red-600'
            case 'high': return 'text-orange-600'
            case 'medium': return 'text-amber-600'
            case 'low': return 'text-emerald-600'
            default: return 'text-accent-blue'
        }
    }

    return (
        <div className={`bg-white border text-sm rounded-lg mb-4 shadow-sm border-l-4 overflow-hidden border-t-border-light border-r-border-light border-b-border-light ${getBorderColor(fix.severity)}`}>
            <div className="p-4 border-b border-border-light bg-slate-50 flex justify-between items-center">
                <div className={`font-bold tracking-tight ${getTextColor(fix.severity)}`}>
                    Recommendation #{index + 1}
                </div>
                <div className="px-2 py-0.5 bg-white border border-border-light rounded text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    {fix.severity} Priority
                </div>
            </div>
            <div className="p-4">
                <div className="text-slate-700 leading-relaxed mb-4">{fix.description}</div>
                {cmds && (
                    <div className="relative bg-slate-900 rounded-md p-4 pt-10 overflow-x-auto">
                        <div className="absolute top-0 left-0 right-0 bg-slate-800 px-4 py-1.5 flex justify-between items-center rounded-t-md border-b border-slate-700">
                            <span className="text-[10px] font-mono text-slate-400">bash</span>
                            <CopyButton text={cmds} />
                        </div>
                        <pre className="font-mono text-[11px] text-emerald-400 m-0">{cmds}</pre>
                    </div>
                )}
            </div>
        </div>
    )
}

function TypewriterText({ text, speed = 10 }) {
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
        <div className="prose prose-sm prose-slate max-w-none text-slate-700">
            <ReactMarkdown
                components={{
                    h1: ({ node, ...props }) => <h1 className="text-xl font-bold text-slate-900 mb-4 pb-2 border-b border-border-light" {...props} />,
                    h2: ({ node, ...props }) => <h2 className="text-lg font-bold text-slate-800 mt-6 mb-3" {...props} />,
                    h3: ({ node, ...props }) => <h3 className="text-base font-semibold text-slate-800 mt-4 mb-2" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-bold text-primary" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-1 mb-4" {...props} />,
                    li: ({ node, ...props }) => <li className="text-slate-700" {...props} />,
                    p: ({ node, ...props }) => <p className="leading-relaxed mb-4" {...props} />,
                    code: ({ node, ...props }) => <code className="font-mono text-[11px] bg-slate-100 text-slate-800 px-1 py-0.5 rounded" {...props} />
                }}
            >
                {displayed}
            </ReactMarkdown>
        </div>
    )
}

export default function ResultCard({ scan, fixes, onExport }) {
    const [tab, setTab] = useState('analysis')
    const findings = fixes?.fixes?.findings || []

    return (
        <div className="bg-white border border-border-light rounded-xl mt-4 max-w-3xl w-full shadow-sm overflow-hidden">
            {/* Tabs */}
            <div className="flex border-b border-border-light bg-slate-50 px-2 lg:px-4 overflow-x-auto">
                {['analysis', 'fixes', 'nmap', 'nikto'].map(t => (
                    <button
                        key={t}
                        className={`px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors
                            ${tab === t
                                ? 'border-accent-blue text-accent-blue'
                                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'}`}
                        onClick={() => setTab(t)}
                    >
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                ))}
                <div className="flex-1" />
                <button
                    onClick={onExport}
                    className="flex items-center gap-2 px-3 py-1.5 my-1.5 bg-white border border-border-light rounded-md text-xs font-bold text-slate-600 hover:bg-slate-50 hover:text-primary transition-colors shadow-sm whitespace-nowrap"
                >
                    <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span>
                    Export PDF
                </button>
            </div>

            {/* Content Area */}
            <div className="p-6 lg:p-8 bg-white max-h-[600px] overflow-y-auto">
                {tab === 'analysis' && (
                    <TypewriterText text={scan.analysis} />
                )}

                {tab === 'fixes' && (
                    <div>
                        {findings.length > 0 ? (
                            findings.map((f, i) => <FixCard key={i} fix={f} index={i} />)
                        ) : (
                            <div className="text-center py-10 text-slate-500 text-sm">No remediation playbooks required for this target.</div>
                        )}

                        {fixes?.fixes?.ai_recommendations && (
                            <div className="mt-8 bg-slate-50 border border-border-light rounded-lg p-6">
                                <div className="flex items-center gap-2 mb-4">
                                    <span className="material-symbols-outlined text-primary">lightbulb</span>
                                    <h3 className="text-sm font-bold text-primary">Strategic Recommendations</h3>
                                </div>
                                <div className="text-sm text-slate-600 leading-relaxed">
                                    {fixes.fixes.ai_recommendations}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {(tab === 'nmap' || tab === 'nikto') && (
                    <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                        <pre className="text-[11px] font-mono text-slate-300 leading-relaxed m-0">
                            {scan[tab] || `No raw ${tab} data available.`}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    )
}
