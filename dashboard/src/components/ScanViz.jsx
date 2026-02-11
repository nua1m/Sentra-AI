const STAGES = [
    { key: 'nmap', label: 'NMAP', icon: '📡' },
    { key: 'nikto', label: 'NIKTO', icon: '🌐' },
    { key: 'ai', label: 'AI', icon: '🧠' },
    { key: 'fixes', label: 'FIXES', icon: '🛡️' },
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

function getStatusMessage(scanStage) {
    const messages = {
        'nmap_running': 'Running Nmap network scan...',
        'nmap_done': 'Nmap complete. Starting Nikto...',
        'nikto_running': 'Running Nikto web vulnerability scan...',
        'nikto_done': 'Nikto complete. Starting AI analysis...',
        'analyzing': 'AI is analyzing the results...',
        'generating_fixes': 'Generating Blue Team fix commands...',
        'complete': 'Scan complete!',
    }
    return messages[scanStage] || 'Preparing scan...'
}

function isConnectorDone(idx, scanStage) {
    const stageMap = {
        'nmap_done': 0, 'nikto_running': 0,
        'nikto_done': 1, 'analyzing': 1,
        'generating_fixes': 2,
        'complete': 3,
    }
    const doneUpTo = stageMap[scanStage] ?? -1
    return idx <= doneUpTo - 1
}

export default function ScanViz({ scanStage }) {
    const isComplete = scanStage === 'complete'

    return (
        <div className="scan-viz">
            <div className="scan-viz-title">
                {isComplete ? '✅ Scan Pipeline Complete' : '⚡ Live Scan Progress'}
            </div>

            <div className="scan-stages">
                {STAGES.map((stage, i) => {
                    const state = getStageState(stage.key, scanStage)
                    return (
                        <div key={stage.key} style={{ display: 'contents' }}>
                            <div className="scan-stage">
                                <div className={`stage-node ${state}`}>
                                    {state === 'done' ? '✓' : stage.icon}
                                </div>
                                <span className={`stage-label ${state}`}>{stage.label}</span>
                            </div>
                            {i < STAGES.length - 1 && (
                                <div className={`stage-connector ${isConnectorDone(i, scanStage) ? 'done' : ''}`} />
                            )}
                        </div>
                    )
                })}
            </div>

            <div className="scan-status-text">
                {!isComplete && <div className="scan-spinner" />}
                {getStatusMessage(scanStage)}
            </div>
        </div>
    )
}
