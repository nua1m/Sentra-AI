import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"

export default function Sidebar({ scans, activeScanId, onSelectScan, onNewScan, onDeleteScan }) {
    // Ensuring latest entries exist first, checking created_at or timestamp
    const sortedScans = [...(scans || [])].sort((a, b) => new Date(b.created_at || b.timestamp || Date.now()) - new Date(a.created_at || a.timestamp || Date.now()))

    return (
        <aside className="w-64 bg-surface border-r border-border-light flex flex-col z-20 shrink-0">
            <div className="p-8 flex items-center gap-3">
                <div className="w-9 h-9 rounded bg-primary dark:bg-white/10 flex items-center justify-center shadow-sm">
                    <span className="material-symbols-outlined text-white text-xl">shield_lock</span>
                </div>
                <div>
                    <h1 className="text-base font-bold tracking-tight text-primary dark:text-white">Sentra AI</h1>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Enterprise</p>
                </div>
            </div>

            <nav className="flex-1 px-4 space-y-1 mt-2 overflow-y-auto">
                {/* Primary Nav Links */}
                <div className="space-y-1 mb-8">
                    <div
                        onClick={onNewScan}
                        className={`flex items-center gap-3 px-4 py-3 rounded-md cursor-pointer transition-all
                            ${!activeScanId ? 'bg-slate-100 dark:bg-white/10 text-primary dark:text-white font-semibold' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 hover:text-primary dark:hover:text-white'}
                        `}
                    >
                        <span className="material-symbols-outlined text-[20px]">dashboard</span>
                        <span className="text-sm">Dashboard</span>
                    </div>
                </div>

                {/* Dynamic Scan History */}
                {sortedScans.length > 0 && (
                    <div className="mb-4">
                        <p className="text-[10px] font-bold text-slate-400 flex items-center gap-2 px-4 mb-2 uppercase tracking-widest">
                            <span className="material-symbols-outlined text-[13px]">history</span>
                            Recent Operations
                        </p>
                        <div className="space-y-1">
                            {sortedScans.map(s => {
                                const validDate = s.created_at || s.timestamp;
                                const timeString = validDate ? new Date(validDate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'NEW';

                                return (
                                    <div
                                        key={s.id}
                                        className={`flex items-center justify-between px-4 py-2.5 rounded-md cursor-pointer transition-colors group ${activeScanId === s.id
                                            ? 'bg-slate-100 dark:bg-white/10 text-primary dark:text-white font-semibold'
                                            : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 hover:text-slate-800 dark:hover:text-white'
                                            }`}
                                    >
                                        <span onClick={() => onSelectScan(s.id)} className="text-[13px] truncate flex-1 min-w-0 pr-2" title={s.target}>{s.target}</span>

                                        <div className="flex items-center gap-1">
                                            <span onClick={() => onSelectScan(s.id)} className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-white/10 text-slate-600 dark:text-slate-400 font-bold uppercase tracking-wide shrink-0 whitespace-nowrap">
                                                {timeString}
                                            </span>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); onDeleteScan(s.id); }}
                                                className="opacity-0 group-hover:opacity-100 hover:text-red-500 text-slate-400 transition-opacity ml-1"
                                                title="Delete log"
                                            >
                                                <span className="material-symbols-outlined text-[14px]">delete</span>
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </nav>

            <div className="p-6 mt-auto border-t border-border-light">
                <SystemStatus />
                <Button
                    onClick={onNewScan}
                    className="w-full flex justify-center items-center gap-2 text-sm font-semibold py-5 rounded transition-all"
                >
                    <span className="material-symbols-outlined text-sm">add</span>
                    New Target
                </Button>
            </div>
        </aside>
    )
}

function SystemStatus() {
    const [health, setHealth] = useState(null)

    useEffect(() => {
        const check = () => fetch('/api/health').then(r => r.json()).then(setHealth).catch(() => setHealth(null))
        check()
        const id = setInterval(check, 10000)
        return () => clearInterval(id)
    }, [])

    const isOnline = health?.status === 'online'

    // Dynamically extract tool statuses from health response
    const toolEntries = health
        ? Object.entries(health)
            .filter(([key]) => key.endsWith('_available'))
            .map(([key, val]) => ({ label: key.replace('_available', '').replace(/^\w/, c => c.toUpperCase()), ok: val }))
        : []

    return (
        <div className="mb-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">System Status</p>
            <div className="space-y-1.5">
                <StatusRow label="API Server" ok={isOnline} />
                {toolEntries.map(t => <StatusRow key={t.label} label={t.label} ok={t.ok} />)}
            </div>
        </div>
    )
}

function StatusRow({ label, ok }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500">{label}</span>
            <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-500' : ok === false ? 'bg-red-500' : 'bg-slate-300'}`} />
                <span className={`text-[10px] font-bold uppercase tracking-wider ${ok ? 'text-emerald-600' : ok === false ? 'text-red-500' : 'text-slate-400'}`}>
                    {ok ? 'Online' : ok === false ? 'Offline' : '...'}
                </span>
            </div>
        </div>
    )
}
