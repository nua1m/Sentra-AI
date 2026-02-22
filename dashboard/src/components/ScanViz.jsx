const STAGES = [
    { key: 'nmap', label: 'Network Scan', sub: 'Discovery' },
    { key: 'nikto', label: 'Web Audit', sub: 'Vulnerability' },
    { key: 'ai', label: 'AI Analysis', sub: 'Threat Intel' },
    { key: 'fixes', label: 'Remediation', sub: 'Playbooks' },
]

function getStageState(stageKey, scanStage) {
    const order = ['nmap', 'nikto', 'ai', 'fixes']
    const stageMap = {
        'nmap_running': { current: 'nmap', doneUpTo: -1 },
        'nmap_done': { current: null, doneUpTo: 0 },
        'nikto_running': { current: 'nikto', doneUpTo: 0 },
        'nikto_done': { current: null, doneUpTo: 1 },
        'analyzing': { current: 'ai', doneUpTo: 1 },
        'generating_fixes': { current: 'fixes', doneUpTo: 2 },
        'complete': { current: null, doneUpTo: 3 },
    }

    const info = stageMap[scanStage] || { current: null, doneUpTo: -1 }
    const idx = order.indexOf(stageKey)

    if (info.current === stageKey) return 'active'
    if (idx <= info.doneUpTo) return 'done'
    return 'pending'
}

function getProgressWidth(scanStage) {
    const stageMap = {
        'nmap_running': 12,
        'nmap_done': 25,
        'nikto_running': 37,
        'nikto_done': 50,
        'analyzing': 62,
        'generating_fixes': 87,
        'complete': 100,
    }
    return stageMap[scanStage] || 0
}

export default function ScanViz({ scanStage }) {
    const isComplete = scanStage === 'complete'
    const progress = getProgressWidth(scanStage)

    return (
        <div className="bg-white border border-border-light rounded-xl p-6 mt-4 max-w-2xl w-full shadow-sm">
            <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary text-xl">
                        {isComplete ? 'task_alt' : 'radar'}
                    </span>
                    <h3 className="font-bold text-slate-800 tracking-tight">
                        {isComplete ? 'Operation Complete' : 'Active Scan Sequence'}
                    </h3>
                </div>
                <div className="px-3 py-1 bg-slate-50 border border-border-light rounded-md flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-500">{progress}%</span>
                    {!isComplete && (
                        <div className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse"></div>
                    )}
                </div>
            </div>

            {/* Pipeline Visualization */}
            <div className="relative mb-6">
                {/* Background Line */}
                <div className="absolute top-4 left-6 right-6 h-1 bg-slate-100 rounded-full z-0"></div>
                {/* Fill Line */}
                <div
                    className="absolute top-4 left-6 h-1 bg-accent-blue rounded-full z-0 transition-all duration-500 ease-in-out"
                    style={{ width: `calc((100% - 3rem) * (${progress} / 100))` }}
                ></div>

                {/* Nodes */}
                <div className="flex justify-between relative z-10 px-2">
                    {STAGES.map((stage) => {
                        const state = getStageState(stage.key, scanStage)
                        return (
                            <div key={stage.key} className="flex flex-col items-center gap-2 w-20">
                                {/* Node Circle */}
                                <div className={`w-8 h-8 rounded-full border-2 bg-white flex items-center justify-center transition-all duration-300
                                    ${state === 'done' ? 'border-emerald-500 text-emerald-500' :
                                        state === 'active' ? 'border-accent-blue text-accent-blue shadow-[0_0_15px_rgba(19,91,236,0.2)]' :
                                            'border-slate-200 text-slate-300'}`}
                                >
                                    {state === 'done' ? (
                                        <span className="material-symbols-outlined text-[16px]">check</span>
                                    ) : state === 'active' ? (
                                        <span className="material-symbols-outlined text-[16px] animate-spin">refresh</span>
                                    ) : (
                                        <div className="w-2 h-2 rounded-full bg-slate-200"></div>
                                    )}
                                </div>

                                {/* Labels */}
                                <div className="text-center">
                                    <p className={`text-[11px] font-bold ${state === 'active' || state === 'done' ? 'text-slate-800' : 'text-slate-400'}`}>
                                        {stage.label}
                                    </p>
                                    <p className="text-[9px] text-slate-400 uppercase tracking-widest mt-0.5">{stage.sub}</p>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* Status Log */}
            <div className="bg-slate-50 rounded-lg p-3 border border-border-light flex gap-3 items-center">
                <span className="material-symbols-outlined text-slate-400 text-sm">terminal</span>
                <p className="text-xs font-mono text-slate-600">
                    <span className="font-bold text-slate-400 mr-2">system&gt;</span>
                    {getStatusText(scanStage)}
                    {!isComplete && <span className="animate-pulse ml-1 text-accent-blue">_</span>}
                </p>
            </div>
        </div>
    )
}

function getStatusText(stage) {
    const map = {
        'nmap_running': 'Executing network discovery and service enumeration...',
        'nmap_done': 'Network discovery complete. Parsing service signatures...',
        'nikto_running': 'Initiating web application vulnerability assessment...',
        'nikto_done': 'Vulnerability profile generated. Aggregating data...',
        'analyzing': 'Synthesizing threat intelligence context...',
        'generating_fixes': 'Drafting autonomous remediation playbooks...',
        'complete': 'All sequences finished. Operation results compiled.',
    }
    return map[stage] || 'Initializing system...'
}
