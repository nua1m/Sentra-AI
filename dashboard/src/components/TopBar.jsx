import { useState, useEffect } from 'react'

function PipelineNode({ label, state }) {
    if (state === 'done') {
        return (
            <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-50 text-emerald-600">
                    <span className="material-symbols-outlined text-[10px] font-bold">check</span>
                </div>
                <span className="text-xs font-semibold text-slate-500">{label}</span>
            </div>
        )
    }
    if (state === 'active') {
        return (
            <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-50 text-primary">
                    <span className="material-symbols-outlined text-[12px] animate-spin" style={{ animationDuration: '3s' }}>sync</span>
                </div>
                <span className="text-xs font-bold text-primary uppercase tracking-tight">{label}</span>
            </div>
        )
    }
    return (
        <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-50 text-slate-300">
                <span className="material-symbols-outlined text-[12px]">hourglass_empty</span>
            </div>
            <span className="text-xs font-semibold text-slate-400">{label}</span>
        </div>
    )
}

function getPipelineStates(stage) {
    if (!stage) return null;
    let net = 'pending', web = 'pending', ai = 'pending';

    if (stage === 'nmap_running') { net = 'active' }
    else if (stage === 'nmap_done' || stage === 'nikto_running') { net = 'done'; web = 'active' }
    else if (stage === 'nikto_done' || stage === 'analyzing') { net = 'done'; web = 'done'; ai = 'active' }
    else if (stage === 'generating_fixes' || stage === 'complete') { net = 'done'; web = 'done'; ai = 'done' }

    return { net, web, ai }
}

export default function TopBar({ scanStage, activeScanId, scans }) {
    const states = getPipelineStates(scanStage)
    const activeScan = scans?.find(s => s.id === activeScanId)

    return (
        <header className="h-16 border-b border-border-light bg-white flex items-center px-10 justify-between shrink-0 z-10 box-border w-full">
            {/* Left side (Pipeline or Context) */}
            <div className="flex items-center gap-8">
                {states ? (
                    <>
                        <div className="flex items-center gap-3 pr-4 border-r border-border-light">
                            <h2 className="text-sm font-bold text-slate-800 truncate max-w-[150px]">{activeScan?.target || 'Target'}</h2>
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] font-bold uppercase tracking-wider">Scanning</span>
                        </div>
                        <div className="flex items-center gap-6">
                            <PipelineNode label="Net Scan" state={states.net} />
                            <div className="w-6 h-px bg-slate-200"></div>
                            <PipelineNode label="Web Vuln" state={states.web} />
                            <div className="w-6 h-px bg-slate-200"></div>
                            <PipelineNode label="AI Analysis" state={states.ai} />
                        </div>
                    </>
                ) : (
                    <div className="flex items-center gap-3">
                        <h2 className="text-sm font-bold text-slate-800">Workspace</h2>
                        <span className="text-slate-300">/</span>
                        <span className="text-sm font-medium text-slate-500">Security Operations overview</span>
                    </div>
                )}
            </div>

            {/* Right side (Profile & Notifications) */}
            <div className="flex items-center gap-5">
                <button className="w-9 h-9 rounded-full border border-border-light flex items-center justify-center text-slate-400 hover:bg-slate-50 transition-colors">
                    <span className="material-symbols-outlined text-xl">notifications</span>
                </button>
                <div className="h-6 w-px bg-border-light"></div>
                <div className="flex items-center gap-3 cursor-pointer group">
                    <div className="text-right">
                        <p className="text-xs font-bold text-primary group-hover:text-accent-blue transition-colors">Admin User</p>
                        <p className="text-[10px] text-slate-400 font-medium tracking-wide">Security Lead</p>
                    </div>
                    {/* Placeholder Avatar */}
                    <div className="w-9 h-9 rounded-full border border-border-light overflow-hidden bg-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                        <img className="w-full h-full object-cover" alt="User profile photo avatar" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDt_IodNWXlCjd5FIZgOpqqXPGczfnajPFZ9nEHrAL29xD3IakxaREc4VfR5_Y_ctPT17ORCnGV21tG-FrylLyKM3H1uRI6nJSLWcneL2UGJl5vJtm7T_TGlNnJrup3tBKOjctELw-fjSaK_j5K7_Kk1rxpg_JiP4LfPu9qSXUgkllNs-9HyE3WlCxiH_O2_CnHzIU48RBDrXcm2kg62MaKaqgYfuzYK0SBAOSez1jI_9uQKL9ZJC2Ss6L5e7Zm-vav27WG2lKVbKYi" />
                    </div>
                </div>
            </div>
        </header>
    )
}
