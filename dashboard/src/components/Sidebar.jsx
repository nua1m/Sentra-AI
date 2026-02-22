import { useEffect } from 'react'

export default function Sidebar({ health, scans, activeScanId, onSelectScan, onNewChat }) {
    return (
        <aside className="sidebar glass-panel" style={{ borderRight: '1px solid var(--border-glass)' }}>
            {/* New Chat */}
            <div
                className={`sidebar-icon ${!activeScanId ? 'active' : ''}`}
                onClick={onNewChat}
                title="New Operation"
            >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 5v14M5 12h14" />
                </svg>
            </div>

            <div style={{ width: '60%', height: '1px', background: 'var(--border-glass)', margin: '0.5rem 0' }} />

            {/* History */}
            <div style={{ flex: 1, overflowY: 'auto', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', paddingTop: '0.5rem' }}>
                {scans.map(scan => (
                    <div
                        key={scan.id}
                        className={`sidebar-icon ${activeScanId === scan.id ? 'active' : ''}`}
                        onClick={() => onSelectScan(scan.id)}
                        title={`${scan.target} (${new Date(scan.created_at).toLocaleTimeString()})`}
                        style={{ position: 'relative' }}
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                            <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                        </svg>
                        {/* Status Dot */}
                        <div style={{
                            position: 'absolute', top: '8px', right: '8px',
                            width: '6px', height: '6px', borderRadius: '50%',
                            backgroundColor: scan.status === 'complete' ? 'var(--safe-green)' : 'var(--warn-yellow)',
                            boxShadow: `0 0 5px ${scan.status === 'complete' ? 'var(--safe-green)' : 'var(--warn-yellow)'}`
                        }} />
                    </div>
                ))}
            </div>
        </aside>
    )
}
