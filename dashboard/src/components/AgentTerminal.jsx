import React, { useEffect, useRef, useState, memo } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Terminal as TerminalIcon, Maximize2, Minimize2 } from 'lucide-react';

const AgentTerminal = memo(function AgentTerminal({ scanId }) {
    const terminalRef = useRef(null);
    const xtermRef = useRef(null);
    const fitAddonRef = useRef(null);
    const socketRef = useRef(null);
    const [isFullscreen, setIsFullscreen] = useState(false);

    useEffect(() => {
        // 1. Initialize xterm.js
        const term = new Terminal({
            theme: {
                background: '#09090b', // zinc-950
                foreground: '#10b981', // emerald-500
                cursor: '#10b981',
                selectionBackground: 'rgba(16, 185, 129, 0.3)',
            },
            fontFamily: '"Fira Code", monospace',
            fontSize: 13,
            cursorBlink: true,
            disableStdin: true,
            scrollback: 10000,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);

        xtermRef.current = term;
        fitAddonRef.current = fitAddon;

        if (terminalRef.current) {
            term.open(terminalRef.current);
            // Delay initial fit so it calculates against the true rendered DOM height
            setTimeout(() => {
                fitAddon.fit();
            }, 100);
        }

        // 2. Connect WebSocket safely preventing Strict Mode double connections
        if (!socketRef.current) {
            const wsUrl = `ws://127.0.0.1:8000/ws/scan/${scanId}`;
            const socket = new WebSocket(wsUrl);
            socketRef.current = socket;

            socket.onopen = () => {
                term.writeln(`\x1b[32m[+] Establish connection to Sentra C2 Server...\x1b[0m`);
                term.writeln(`\x1b[32m[+] Target Session ID: ${scanId}\x1b[0m`);
            };

            socket.onmessage = (event) => {
                term.write(event.data);
            };

            socket.onclose = () => {
                term.writeln(`\r\n\x1b[33m[-] Connection closed. Scan complete.\x1b[0m`);
            };

            socket.onerror = (err) => {
                term.writeln(`\r\n\x1b[31m[!] WebSocket Error occurred.\x1b[0m`);
            };
        }

        // 3. Handle resize
        const handleResize = () => {
            if (fitAddonRef.current) {
                fitAddonRef.current.fit();
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (socketRef.current) {
                socketRef.current.close();
                socketRef.current = null;
            }
            term.dispose();
        };
    }, [scanId]);

    // Adjust fit when fullscreen toggles
    useEffect(() => {
        if (fitAddonRef.current) {
            setTimeout(() => fitAddonRef.current.fit(), 50);
        }
    }, [isFullscreen]);

    return (
        <div
            className={`border border-border-light bg-zinc-950 overflow-hidden flex flex-col shadow-2xl transition-all duration-300 ${isFullscreen ? 'fixed inset-4 z-50 rounded-lg' : 'relative rounded-xl my-4 h-[300px]'
                }`}
        >
            {/* Mac-like Window Header */}
            <div className="h-10 bg-surface border-b border-border-light flex items-center justify-between px-4 shrink-0 select-none">
                <div className="flex items-center gap-2">
                    <TerminalIcon className="w-4 h-4 text-primary" />
                    <span className="text-xs font-medium text-slate-400 dark:text-zinc-400 font-mono tracking-wider">
                        root@sentra-c2:~
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setIsFullscreen(!isFullscreen)}
                        className="text-slate-400 hover:text-primary transition-colors"
                    >
                        {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                    </button>
                    <div className="flex gap-1.5 ml-2">
                        <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                        <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                        <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                    </div>
                </div>
            </div>

            {/* Terminal Container */}
            <div className="flex-1 p-2 relative overflow-hidden bg-[#09090b]">
                {isFullscreen && (
                    <div className="absolute inset-0 bg-[#09090b] pointer-events-none -mr-4 -mb-4"></div>
                )}
                <div ref={terminalRef} className="w-full h-full relative z-10" />
            </div>
        </div>
    );
});

export default AgentTerminal;
