import { useState, useEffect } from 'react'
import { useTheme } from './theme-provider'
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

function PipelineNode({ label, state }) {
    if (state === 'done') {
        return (
            <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <span className="material-symbols-outlined text-[10px] font-bold">check</span>
                </div>
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{label}</span>
            </div>
        )
    }
    if (state === 'active') {
        return (
            <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-50 dark:bg-white/10 text-primary dark:text-white">
                    <span className="material-symbols-outlined text-[12px] animate-spin" style={{ animationDuration: '3s' }}>sync</span>
                </div>
                <span className="text-xs font-bold text-primary dark:text-white uppercase tracking-tight">{label}</span>
            </div>
        )
    }
    return (
        <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-50 dark:bg-white/5 text-slate-300 dark:text-slate-500">
                <span className="material-symbols-outlined text-[12px]">hourglass_empty</span>
            </div>
            <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">{label}</span>
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
    const { theme, setTheme } = useTheme()

    return (
        <header className="h-16 border-b border-border-light bg-surface flex items-center px-10 justify-between shrink-0 z-10 box-border w-full">
            {/* Left side (Pipeline or Context) */}
            <div className="flex items-center gap-8">
                {states ? (
                    <>
                        <div className="flex items-center gap-3 pr-4 border-r border-border-light">
                            <h2 className="text-sm font-bold text-slate-800 dark:text-white truncate max-w-[150px]">{activeScan?.target || 'Target'}</h2>
                            <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/10 text-slate-500 dark:text-slate-300 rounded text-[10px] font-bold uppercase tracking-wider">Scanning</span>
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
                        <h2 className="text-sm font-bold text-slate-800 dark:text-white">Workspace</h2>
                        <span className="text-slate-300 dark:text-slate-600">/</span>
                        <span className="text-sm font-medium text-slate-500 dark:text-slate-400">Security Operations overview</span>
                    </div>
                )}
            </div>

            {/* Right side (Profile & Notifications) */}
            <div className="flex items-center gap-5">
                <ToggleGroup
                    type="single"
                    value={theme}
                    onValueChange={(val) => { if (val) setTheme(val) }}
                    className="flex p-1 bg-slate-100 dark:bg-accent rounded-md border border-border-light shadow-sm"
                >
                    <ToggleGroupItem
                        value="light"
                        aria-label="Light mode"
                        className="h-7 w-8 px-0 data-[state=on]:bg-white data-[state=on]:dark:bg-slate-700 data-[state=on]:shadow-sm data-[state=on]:text-slate-900 data-[state=on]:dark:text-white text-slate-500 rounded-sm transition-all"
                    >
                        <span className="material-symbols-outlined text-[16px]">light_mode</span>
                    </ToggleGroupItem>
                    <ToggleGroupItem
                        value="dark"
                        aria-label="Dark mode"
                        className="h-7 w-8 px-0 data-[state=on]:bg-white data-[state=on]:dark:bg-slate-700 data-[state=on]:shadow-sm data-[state=on]:text-slate-900 data-[state=on]:dark:text-white text-slate-500 rounded-sm transition-all"
                    >
                        <span className="material-symbols-outlined text-[16px]">dark_mode</span>
                    </ToggleGroupItem>
                </ToggleGroup>
                <div className="h-6 w-px bg-border-light"></div>
                <div className="flex items-center gap-3 cursor-pointer group">
                    <div className="text-right">
                        <p className="text-xs font-bold text-primary dark:text-white group-hover:text-accent-blue transition-colors">Admin User</p>
                        <p className="text-[10px] text-slate-400 font-medium tracking-wide">Security Lead</p>
                    </div>
                    {/* Placeholder Avatar */}
                    <div className="w-9 h-9 rounded-full border border-border-light overflow-hidden bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 shrink-0">
                        <img className="w-full h-full object-cover" alt="User profile photo avatar" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDt_IodNWXlCjd5FIZgOpqqXPGczfnajPFZ9nEHrAL29xD3IakxaREc4VfR5_Y_ctPT17ORCnGV21tG-FrylLyKM3H1uRI6nJSLWcneL2UGJl5vJtm7T_TGlNnJrup3tBKOjctELw-fjSaK_j5K7_Kk1rxpg_JiP4LfPu9qSXUgkllNs-9HyE3WlCxiH_O2_CnHzIU48RBDrXcm2kg62MaKaqgYfuzYK0SBAOSez1jI_9uQKL9ZJC2Ss6L5e7Zm-vav27WG2lKVbKYi" />
                    </div>
                </div>
            </div>
        </header>
    )
}
