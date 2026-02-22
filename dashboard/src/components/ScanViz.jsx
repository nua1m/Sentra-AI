const STAGES = [
    { key: 'nmap', label: 'NET.SCAN', sub: 'PORT DISCOVERY' },
    { key: 'nikto', label: 'WEB.VULN', sub: 'CGI/SSL AUDIT' },
    { key: 'ai', label: 'AI.ANALYSIS', sub: 'THREAT INTEL' },
    { key: 'fixes', label: 'GEN.FIXES', sub: 'BLUE TEAM OPS' },
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
        <div className="viz-hud">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <div style={{ fontFamily: 'Orbitron', fontSize: '0.8rem', color: isComplete ? 'var(--safe-green)' : 'var(--primary-cyan)' }}>
                    {isComplete ? 'MISSION COMPLETE' : 'SEQUENCE RUNNING...'}
                </div>
                <div style={{ fontFamily: 'JetBrains Mono', fontSize: '0.7rem', color: 'var(--primary-cyan)' }}>
                    {progress}%
                </div>
            </div>

            <div className="pipeline-track">
                <div className="pipeline-line" />
                <div className="pipeline-line-fill" style={{ width: `${progress}%` }} />

                {STAGES.map((stage) => {
                    const state = getStageState(stage.key, scanStage)
                    return (
                        <div key={stage.key} className={`pipeline-step ${state}`}>
                            <div className="step-box">
                                <div style={{ fontWeight: 700 }}>{stage.label}</div>
                                <div style={{ fontSize: '0.55rem', opacity: 0.7 }}>{stage.sub}</div>
                            </div>
                            {state === 'active' && <div className="text-glow" style={{ fontSize: '10px' }}>EXECUTING</div>}
                        </div>
                    )
                })}
            </div>

            <div style={{
                fontFamily: 'JetBrains Mono', fontSize: '0.75rem', color: 'var(--text-dim)',
                borderTop: '1px solid var(--border-glass)', paddingTop: '0.8rem', marginTop: '0.5rem',
                display: 'flex', gap: '0.5rem', alignItems: 'center'
            }}>
                <span style={{ color: 'var(--primary-cyan)' }}>ROOT@SENTRA:~$</span>
                <span className={!isComplete ? "typing-cursor" : ""}>
                    {getStatusText(scanStage)}
                </span>
            </div>
        </div>
    )
}

function getStatusText(stage) {
    const map = {
        'nmap_running': 'exec nmap -sV -p- --script vuln <TARGET>',
        'nmap_done': 'nmap process finished. exit code 0.',
        'nikto_running': 'EXEC NIKTO WEB AUDIT (MAX 60s)...',
        'nikto_done': 'nikto export generated. parsing xml...',
        'analyzing': 'initiating neural analysis context...',
        'generating_fixes': 'querying remediation database...',
        'complete': 'all sequences finished. ready for report.',
    }
    return map[stage] || 'initializing scan sequence...'
}
