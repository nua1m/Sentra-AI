import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false)
    return (
        <Button
            variant="secondary"
            size="sm"
            className="absolute top-2 right-2 h-6 px-2 text-[10px] uppercase gap-1"
            onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        >
            <span className="material-symbols-outlined text-[12px]">{copied ? 'check' : 'content_copy'}</span>
            {copied ? 'Copied' : 'Copy'}
        </Button>
    )
}

function FixCard({ fix, index }) {
    const cmds = fix.commands?.filter(c => c.trim()).join('\n') || ''

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
        <div className={`bg-surface border text-sm rounded-lg mb-4 shadow-sm border-l-4 overflow-hidden border-t-border-light border-r-border-light border-b-border-light ${getBorderColor(fix.severity)}`}>
            <div className="p-4 border-b border-border-light bg-slate-50 dark:bg-black/20 flex justify-between items-center">
                <div className={`font-bold tracking-tight ${getTextColor(fix.severity)}`}>
                    Recommendation #{index + 1}
                </div>
                <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
                    {fix.severity} Priority
                </Badge>
            </div>
            <div className="p-4">
                <div className="text-slate-700 dark:text-slate-300 leading-relaxed mb-4">{fix.description}</div>
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

// Typewriter that animates once on mount, then holds the full text permanently
function TypewriterText({ text, speed = 10 }) {
    const [displayed, setDisplayed] = useState('')
    const hasAnimated = useRef(false)

    useEffect(() => {
        if (hasAnimated.current) {
            setDisplayed(text)
            return
        }
        let i = 0
        setDisplayed('')
        const interval = setInterval(() => {
            setDisplayed(text.slice(0, i))
            i += speed
            if (i > text.length) {
                clearInterval(interval)
                hasAnimated.current = true
            }
        }, 10)
        return () => clearInterval(interval)
    }, [text, speed])

    return (
        <div className="prose prose-sm prose-slate max-w-none text-slate-700 dark:text-slate-300">
            <ReactMarkdown
                components={{
                    h1: ({ node, ...props }) => <h1 className="text-xl font-bold text-slate-900 dark:text-white mb-4 pb-2 border-b border-border-light" {...props} />,
                    h2: ({ node, ...props }) => <h2 className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-6 mb-3" {...props} />,
                    h3: ({ node, ...props }) => <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200 mt-4 mb-2" {...props} />,
                    strong: ({ node, ...props }) => <strong className="font-bold text-primary dark:text-white" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc pl-5 space-y-1 mb-4" {...props} />,
                    li: ({ node, ...props }) => <li className="text-slate-700 dark:text-slate-300" {...props} />,
                    p: ({ node, ...props }) => <p className="leading-relaxed mb-4" {...props} />,
                    code: ({ node, ...props }) => <code className="font-mono text-[11px] bg-slate-100 dark:bg-white/10 text-slate-800 dark:text-slate-200 px-1 py-0.5 rounded" {...props} />
                }}
            >
                {displayed}
            </ReactMarkdown>
        </div>
    )
}

const TABS = [
    { id: 'analysis', label: 'Analysis', icon: 'analytics' },
    { id: 'fixes', label: 'Fixes', icon: 'build' },
    { id: 'nmap', label: 'Nmap', icon: 'lan' },
    { id: 'nikto', label: 'Nikto', icon: 'language' },
]

export default function ResultCard({ scan, fixes, onExport }) {
    const [activeTab, setActiveTab] = useState('analysis')
    const findings = fixes?.fixes?.findings || []
    const riskScore = scan.risk_score ?? null
    const riskLabel = scan.risk_label ?? ''

    const getRiskColor = (label) => {
        switch (label) {
            case 'CRITICAL': return { bg: 'bg-red-50 dark:bg-red-500/10', text: 'text-red-600 dark:text-red-400', border: 'border-red-200 dark:border-red-500/20' }
            case 'HIGH': return { bg: 'bg-orange-50 dark:bg-orange-500/10', text: 'text-orange-600 dark:text-orange-400', border: 'border-orange-200 dark:border-orange-500/20' }
            case 'MEDIUM': return { bg: 'bg-amber-50 dark:bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', border: 'border-amber-200 dark:border-amber-500/20' }
            case 'LOW': return { bg: 'bg-emerald-50 dark:bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', border: 'border-emerald-200 dark:border-emerald-500/20' }
            default: return { bg: 'bg-slate-50', text: 'text-slate-500', border: 'border-slate-200' }
        }
    }

    const riskColors = getRiskColor(riskLabel)

    return (
        <Card className="mt-4 max-w-3xl w-full overflow-hidden border-border-light shadow-sm">
            {/* Risk Score Banner */}
            {riskScore !== null && (
                <div className={`flex items-center justify-between px-6 py-4 border-b ${riskColors.border} ${riskColors.bg}`}>
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${riskColors.bg} border ${riskColors.border}`}>
                            <span className={`material-symbols-outlined text-xl ${riskColors.text}`}>shield</span>
                        </div>
                        <div>
                            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Security Risk Assessment</p>
                            <p className={`text-lg font-bold ${riskColors.text}`}>{riskScore}/10 — {riskLabel}</p>
                        </div>
                    </div>
                    <div className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest ${riskColors.text} ${riskColors.bg} border ${riskColors.border}`}>
                        {riskLabel} RISK
                    </div>
                </div>
            )}

            {/* Tab Bar — manual state, no Radix mount/unmount */}
            <div className="flex items-center border-b border-border-light bg-white dark:bg-zinc-900 px-2">
                <div className="flex items-center gap-1 flex-1 overflow-x-auto h-12">
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-semibold rounded-md transition-colors whitespace-nowrap
                                ${activeTab === tab.id
                                    ? 'bg-primary/10 text-primary'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5'
                                }`}
                        >
                            <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
                            {tab.label}
                        </button>
                    ))}
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={onExport}
                    className="gap-1.5 text-xs font-bold ml-2 shrink-0"
                >
                    <span className="material-symbols-outlined text-[14px]">download</span>
                    PDF
                </Button>
            </div>

            {/* Content — all panels always mounted, visibility toggled via CSS */}
            <div className="w-full min-h-[400px] max-h-[600px] overflow-y-auto bg-white dark:bg-zinc-950">
                {/* Analysis — always mounted so TypewriterText ref persists */}
                <div className={`p-6 lg:p-8 ${activeTab === 'analysis' ? 'block' : 'hidden'}`}>
                    <TypewriterText text={scan.analysis} />
                </div>

                {/* Fixes */}
                <div className={`p-6 lg:p-8 ${activeTab === 'fixes' ? 'block' : 'hidden'}`}>
                    {findings.length > 0 ? (
                        findings.map((f, i) => <FixCard key={i} fix={f} index={i} />)
                    ) : (
                        <div className="text-center py-10 text-slate-500 text-sm">No remediation playbooks required for this target.</div>
                    )}
                    {fixes?.fixes?.ai_recommendations && (
                        <div className="mt-8 bg-slate-50 dark:bg-black/20 border border-border-light rounded-lg p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <span className="material-symbols-outlined text-primary dark:text-white">lightbulb</span>
                                <h3 className="text-sm font-bold text-primary dark:text-white">Strategic Recommendations</h3>
                            </div>
                            <div className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                                {fixes.fixes.ai_recommendations}
                            </div>
                        </div>
                    )}
                </div>

                {/* Nmap */}
                <div className={`p-6 lg:p-8 ${activeTab === 'nmap' ? 'block' : 'hidden'}`}>
                    <div className="bg-zinc-900 rounded-lg p-5 border border-zinc-800 overflow-hidden">
                        <pre className="text-[11px] font-mono text-slate-300 leading-relaxed m-0 whitespace-pre-wrap break-all">
                            {scan['nmap'] || 'No raw nmap data available.'}
                        </pre>
                    </div>
                </div>

                {/* Nikto */}
                <div className={`p-6 lg:p-8 ${activeTab === 'nikto' ? 'block' : 'hidden'}`}>
                    <div className="bg-zinc-900 rounded-lg p-5 border border-zinc-800 overflow-hidden">
                        <pre className="text-[11px] font-mono text-slate-300 leading-relaxed m-0 whitespace-pre-wrap break-all">
                            {scan['nikto'] || 'No raw nikto data available.'}
                        </pre>
                    </div>
                </div>
            </div>
        </Card>
    )
}
