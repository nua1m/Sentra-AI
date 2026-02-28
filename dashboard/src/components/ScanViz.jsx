import { Card } from "@/components/ui/card"

// Default stages — will be filtered based on what tools are actually being used
const ALL_STAGES = {
    nmap: { key: 'nmap', label: 'Network Scan', sub: 'Nmap', icon: 'lan' },
    nikto: { key: 'nikto', label: 'Web Audit', sub: 'Nikto', icon: 'language' },
    sslscan: { key: 'sslscan', label: 'TLS Audit', sub: 'SSLScan', icon: 'lock' },
    gobuster: { key: 'gobuster', label: 'Dir Enum', sub: 'Gobuster', icon: 'folder_open' },
    ai: { key: 'ai', label: 'AI Analysis', sub: 'Threat Intel', icon: 'psychology' },
    fixes: { key: 'fixes', label: 'Remediation', sub: 'Playbooks', icon: 'build' },
}

function buildStages(toolsUsed) {
    // Build dynamic stages from tools_used array
    const stages = []

    // Add tool stages in order
    const toolOrder = ['nmap', 'nikto', 'sslscan', 'gobuster']
    for (const tool of toolOrder) {
        if (toolsUsed.includes(tool) && ALL_STAGES[tool]) {
            stages.push(ALL_STAGES[tool])
        }
    }

    // Always add AI + Fixes at the end
    stages.push(ALL_STAGES.ai)
    stages.push(ALL_STAGES.fixes)

    return stages
}

function getStageState(stageKey, scanStage, stages) {
    const order = stages.map(s => s.key)
    const idx = order.indexOf(stageKey)

    // Map scan_stage values to current/done states
    for (let i = 0; i < order.length; i++) {
        const key = order[i]
        if (scanStage === `${key}_running`) {
            if (stageKey === key) return 'active'
            return idx < i ? 'done' : 'pending'
        }
        if (scanStage === `${key}_done`) {
            return idx <= i ? 'done' : 'pending'
        }
    }

    // Handle special stages
    if (scanStage === 'analyzing') {
        const aiIdx = order.indexOf('ai')
        if (stageKey === 'ai') return 'active'
        return idx < aiIdx ? 'done' : 'pending'
    }
    if (scanStage === 'generating_fixes') {
        const fixIdx = order.indexOf('fixes')
        if (stageKey === 'fixes') return 'active'
        return idx < fixIdx ? 'done' : 'pending'
    }
    if (scanStage === 'complete') return 'done'

    return 'pending'
}

function getProgressWidth(scanStage, stages) {
    const total = stages.length
    const order = stages.map(s => s.key)

    for (let i = 0; i < order.length; i++) {
        const key = order[i]
        if (scanStage === `${key}_running`) {
            return Math.round(((i + 0.5) / total) * 100)
        }
        if (scanStage === `${key}_done`) {
            return Math.round(((i + 1) / total) * 100)
        }
    }

    if (scanStage === 'analyzing') {
        const aiIdx = order.indexOf('ai')
        return Math.round(((aiIdx + 0.5) / total) * 100)
    }
    if (scanStage === 'generating_fixes') {
        const fixIdx = order.indexOf('fixes')
        return Math.round(((fixIdx + 0.5) / total) * 100)
    }
    if (scanStage === 'complete') return 100

    return 0
}

export default function ScanViz({ scanStage, toolsUsed }) {
    const isComplete = scanStage === 'complete'
    const stages = buildStages(toolsUsed || ['nmap'])
    const progress = getProgressWidth(scanStage, stages)

    return (
        <Card className="p-0 mt-4 max-w-3xl w-full overflow-hidden border-border-light shadow-sm">
            {/* Header */}
            <div className="flex justify-between items-center px-6 pt-5 pb-4">
                <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isComplete ? 'bg-emerald-50 dark:bg-emerald-500/10' : 'bg-blue-50 dark:bg-blue-500/10'}`}>
                        <span className={`material-symbols-outlined text-lg ${isComplete ? 'text-emerald-500' : 'text-accent-blue'}`}>
                            {isComplete ? 'verified' : 'radar'}
                        </span>
                    </div>
                    <div>
                        <h3 className="font-bold text-sm text-slate-800 dark:text-white tracking-tight">
                            {isComplete ? 'Operation Complete' : 'Active Scan Sequence'}
                        </h3>
                        <p className="text-[11px] text-slate-400 mt-0.5">Autonomous security pipeline</p>
                    </div>
                </div>
                <div className={`text-xs font-bold px-3 py-1.5 rounded-full ${isComplete
                    ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400'
                    : 'bg-blue-50 text-accent-blue dark:bg-blue-500/10'
                    }`}>
                    {progress}%
                </div>
            </div>

            {/* Progress Bar */}
            <div className="px-6 pb-4">
                <div className="w-full h-1.5 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                    <div
                        className={`h-full rounded-full transition-all duration-700 ease-out ${isComplete ? 'bg-emerald-500' : 'bg-accent-blue'}`}
                        style={{ width: `${progress}%` }}
                    />
                </div>
            </div>

            {/* Pipeline Nodes — dynamic grid based on number of stages */}
            <div className="px-4 pb-5">
                <div className={`grid gap-2`} style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }}>
                    {stages.map((stage) => {
                        const state = getStageState(stage.key, scanStage, stages)
                        return (
                            <div
                                key={stage.key}
                                className={`flex flex-col items-center gap-2 py-3 px-2 rounded-lg transition-all duration-300
                                    ${state === 'active' ? 'bg-blue-50 dark:bg-blue-500/5' :
                                        state === 'done' ? 'bg-emerald-50/50 dark:bg-emerald-500/5' :
                                            ''}`}
                            >
                                {/* Icon */}
                                <div className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300
                                    ${state === 'done' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
                                        state === 'active' ? 'bg-blue-100 dark:bg-blue-500/20 text-accent-blue shadow-sm' :
                                            'bg-slate-100 dark:bg-white/5 text-slate-300 dark:text-slate-600'}`}
                                >
                                    {state === 'done' ? (
                                        <span className="material-symbols-outlined text-[18px]">check</span>
                                    ) : state === 'active' ? (
                                        <span className="material-symbols-outlined text-[18px] animate-spin" style={{ animationDuration: '2s' }}>progress_activity</span>
                                    ) : (
                                        <span className="material-symbols-outlined text-[18px]">{stage.icon}</span>
                                    )}
                                </div>

                                {/* Labels */}
                                <div className="text-center">
                                    <p className={`text-[11px] font-bold leading-tight ${state === 'active' ? 'text-accent-blue' :
                                        state === 'done' ? 'text-slate-700 dark:text-slate-200' :
                                            'text-slate-400 dark:text-slate-500'
                                        }`}>
                                        {stage.label}
                                    </p>
                                    <p className="text-[9px] text-slate-400 uppercase tracking-widest mt-0.5">{stage.sub}</p>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* Status Bar */}
            <div className="bg-slate-50 dark:bg-black/20 px-5 py-3 border-t border-border-light min-h-[44px] flex items-center gap-3">
                <span className="material-symbols-outlined text-slate-400 text-sm">terminal</span>
                <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                    <span className="font-bold text-slate-400 dark:text-slate-500 mr-1.5">$</span>
                    {getStatusText(scanStage)}
                    {!isComplete && <span className="animate-pulse ml-1 text-accent-blue">▊</span>}
                </p>
            </div>
        </Card>
    )
}

function getStatusText(stage) {
    // Handle dynamic tool stages
    if (stage?.endsWith('_running')) {
        const tool = stage.replace('_running', '')
        return `Running ${tool} scan...`
    }
    if (stage?.endsWith('_done')) {
        const tool = stage.replace('_done', '')
        return `${tool} scan complete. Parsing output...`
    }

    const map = {
        'analyzing': 'AI engine processing threat intelligence...',
        'generating_fixes': 'Generating remediation playbooks...',
        'complete': 'All phases complete. Report ready.',
    }
    return map[stage] || 'Initializing pipeline...'
}
