import { useState, useEffect } from 'react'
import { fetchHealth } from '../api'

export default function TopBar() {
    const [health, setHealth] = useState(null)
    const [time, setTime] = useState(new Date())

    useEffect(() => {
        fetchHealth().then(setHealth).catch(() => setHealth(null))
        const interval = setInterval(() => {
            fetchHealth().then(setHealth).catch(() => setHealth(null))
            setTime(new Date())
        }, 1000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="top-hud glass-panel">
            <div className="hud-group">
                <div className="hud-item" style={{ fontFamily: 'Orbitron', fontWeight: 700, letterSpacing: '2px', color: 'var(--primary-cyan)' }}>
                    SENTRA.AI <span style={{ color: 'var(--text-muted)', fontSize: '0.6rem', alignSelf: 'center', marginLeft: '0.5rem' }}>V1.0.0</span>
                </div>
                <div className="hud-item">
                    SECURE CONNECTION: <span className="hud-val" style={{ color: health ? 'var(--safe-green)' : 'var(--alert-red)' }}>
                        {health ? 'ESTABLISHED' : 'OFFLINE'}
                    </span>
                </div>
            </div>

            <div className="hud-group">
                <div className="hud-item">
                    ACTIVE TARGETS: <span className="hud-val">{health?.active_scans || 0}</span>
                </div>
                <div className="hud-item">
                    SYS.TIME: <span className="hud-val">{time.toLocaleTimeString('en-GB')}</span>
                </div>
            </div>
        </div>
    )
}
