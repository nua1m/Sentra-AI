import { useEffect } from 'react'
import { fetchScans } from '../api'

function formatDate(iso) {
    if (!iso) return ''
    const d = new Date(iso)
    const now = new Date()
    const isToday = d.toDateString() === now.toDateString()
    if (isToday) return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

export default function Sidebar({ health, scans, activeScanId, onSelectScan, onNewChat }) {
    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="sidebar-logo">S</div>
                <div className="sidebar-brand">Sentra<span>.AI</span></div>
            </div>

            <div className="sidebar-status">
                <div className={`status-dot ${health ? '' : 'offline'}`}></div>
                {health ? 'System Online' : 'Offline'}
            </div>

            <button className="new-chat-btn" onClick={onNewChat}>
                + New Chat
            </button>

            <div className="sidebar-label">Scan History</div>

            <div className="scan-history">
                {scans.length === 0 ? (
                    <div style={{ padding: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                        No scans yet
                    </div>
                ) : (
                    scans.map(scan => (
                        <div
                            key={scan.id}
                            className={`history-item ${activeScanId === scan.id ? 'active' : ''}`}
                            onClick={() => onSelectScan(scan.id)}
                        >
                            <div className="history-icon">
                                {scan.status === 'complete' ? '✓' : '◉'}
                            </div>
                            <div className="history-info">
                                <div className="history-target">{scan.target}</div>
                                <div className="history-date">{formatDate(scan.created_at)}</div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </aside>
    )
}
