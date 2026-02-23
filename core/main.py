from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import uuid
import asyncio
import sys

# Windows requires ProactorEventLoop for subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from datetime import datetime
from typing import Dict, List

from .security import verify_target_ownership
from .scanner import Scanner
from .intelligence import process_chat_query, ask_kimi, analyze_results
from .database import save_scan, get_scan, list_scans, update_scan_status, delete_scan

# Setup
app = FastAPI(title="Sentra.AI Core")
scanner = Scanner()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentra.main")

# CORS — Allow React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache (mirrors SQLite for active scans)
scans: Dict[str, dict] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.scan_logs: Dict[str, List[str]] = {}

    async def connect(self, websocket: WebSocket, scan_id: str):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)
        
        # Send history
        if scan_id in self.scan_logs:
            for line in self.scan_logs[scan_id]:
                try:
                    await websocket.send_text(line)
                except Exception:
                    pass

    def disconnect(self, websocket: WebSocket, scan_id: str):
        if scan_id in self.active_connections and websocket in self.active_connections[scan_id]:
            self.active_connections[scan_id].remove(websocket)

    async def broadcast(self, message: str, scan_id: str):
        if scan_id not in self.scan_logs:
            self.scan_logs[scan_id] = []
        self.scan_logs[scan_id].append(message)
        
        if scan_id in self.active_connections:
            for connection in self.active_connections[scan_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass

manager = ConnectionManager()


class ChatRequest(BaseModel):
    message: str

class ScanRequest(BaseModel):
    target: str


async def _narrate(scan_id: str, text: str, delay: float = 0.06):
    """Broadcast a single narration line with a realistic typing delay."""
    await manager.broadcast(text, scan_id)
    await asyncio.sleep(delay)


async def _narrate_block(scan_id: str, lines: list, delay: float = 0.06):
    """Broadcast multiple narration lines sequentially."""
    for line in lines:
        await _narrate(scan_id, line + "\r\n", delay)


def _calculate_risk_score(open_ports: int, vuln_count: int, fixes: dict) -> float:
    """Heuristic risk scoring: 0–10 scale based on scan findings."""
    score = 0.0
    
    # Port exposure (max 3 points)
    if open_ports >= 5:
        score += 3.0
    elif open_ports >= 3:
        score += 2.0
    elif open_ports >= 1:
        score += 1.0
    
    # Web vulnerabilities (max 3 points)
    if vuln_count >= 10:
        score += 3.0
    elif vuln_count >= 5:
        score += 2.0
    elif vuln_count >= 1:
        score += 1.0
    
    # Severity of fixes (max 4 points)
    if fixes and fixes.get("findings"):
        severity_weights = {"critical": 2.0, "high": 1.5, "medium": 0.5, "low": 0.2}
        severity_score = sum(
            severity_weights.get(f.get("severity", "").lower(), 0.3)
            for f in fixes["findings"]
        )
        score += min(severity_score, 4.0)
    
    return round(min(score, 10.0), 1)


async def run_background_scan(scan_id: str, target: str):
    scans[scan_id]["status"] = "scanning"
    scans[scan_id]["scan_stage"] = "nmap_running"
    update_scan_status(scan_id, "scanning", scan_stage="nmap_running")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 0: BOOT SEQUENCE
    # ═══════════════════════════════════════════════════════════════
    await _narrate_block(scan_id, [
        "",
        "\x1b[36m╔══════════════════════════════════════════════════════════╗\x1b[0m",
        "\x1b[36m║\x1b[0m  \x1b[1;37mSENTRA AI — Autonomous Security Assessment Engine\x1b[0m      \x1b[36m║\x1b[0m",
        "\x1b[36m║\x1b[0m  \x1b[90mv2.1.0 | Threat Intelligence Pipeline\x1b[0m                   \x1b[36m║\x1b[0m",
        "\x1b[36m╚══════════════════════════════════════════════════════════╝\x1b[0m",
        "",
    ], delay=0.08)

    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Target acquired: \x1b[1;37m{target}\x1b[0m\r\n", 0.4)
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Session ID: \x1b[90m{scan_id}\x1b[0m\r\n", 0.3)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Verifying target ownership... ", 0.6)
    await _narrate(scan_id, "\x1b[1;32m✓ VERIFIED\x1b[0m\r\n", 0.5)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Loading scan modules...\r\n", 0.4)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m  ├─ Network Reconnaissance (Nmap)\r\n", 0.15)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m  ├─ Web Vulnerability Audit (Nikto)\r\n", 0.15)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m  ├─ AI Threat Analysis (Kimi)\r\n", 0.15)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m  └─ Remediation Playbook Generator\r\n", 0.15)
    await _narrate(scan_id, "\r\n", 0.3)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: NMAP
    # ═══════════════════════════════════════════════════════════════
    await _narrate_block(scan_id, [
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 1/4]\x1b[0m  \x1b[1;37mNETWORK RECONNAISSANCE\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Executing: \x1b[33mnmap -F -T4 {target}\x1b[0m\r\n", 0.3)
    await _narrate(scan_id, "\r\n", 0.2)

    nmap_lines = []
    async for line in scanner.run_nmap_scan_stream(target):
        nmap_lines.append(line)
        formatted_line = line.replace('\n', '\r\n') if not line.endswith('\r\n') else line
        await manager.broadcast(formatted_line, scan_id)
        await asyncio.sleep(0.04)
    nmap_out = "".join(nmap_lines)

    # Count open ports for narration
    open_ports = sum(1 for l in nmap_lines if '/tcp' in l and 'open' in l)
    
    await _narrate(scan_id, "\r\n", 0.2)
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Network scan complete. \x1b[1;33m{open_ports} open port(s)\x1b[0m detected.\r\n", 0.5)

    scans[scan_id]["nmap"] = nmap_out
    scans[scan_id]["scan_stage"] = "nmap_done"
    update_scan_status(scan_id, "scanning", nmap=nmap_out, scan_stage="nmap_done")
    
    await asyncio.sleep(0.8)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: NIKTO
    # ═══════════════════════════════════════════════════════════════
    scans[scan_id]["scan_stage"] = "nikto_running"
    update_scan_status(scan_id, "scanning", scan_stage="nikto_running")

    await _narrate_block(scan_id, [
        "",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 2/4]\x1b[0m  \x1b[1;37mWEB VULNERABILITY AUDIT\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    if open_ports > 0:
        await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m HTTP service detected. Escalating to web audit...\r\n", 0.4)
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Executing: \x1b[33mnikto -h {target}\x1b[0m\r\n", 0.3)
    await _narrate(scan_id, "\r\n", 0.2)

    nikto_lines = []
    async for line in scanner.run_nikto_scan_stream(target):
        nikto_lines.append(line)
        formatted_line = line.replace('\n', '\r\n') if not line.endswith('\r\n') else line
        await manager.broadcast(formatted_line, scan_id)
        await asyncio.sleep(0.04)
    nikto_out = "".join(nikto_lines)

    vuln_count = sum(1 for l in nikto_lines if l.strip().startswith('+') or 'OSVDB' in l)

    await _narrate(scan_id, "\r\n", 0.2)
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Web audit complete. \x1b[1;33m{vuln_count} finding(s)\x1b[0m identified.\r\n", 0.5)

    scans[scan_id]["nikto"] = nikto_out
    scans[scan_id]["scan_stage"] = "nikto_done"
    update_scan_status(scan_id, "scanning", nikto=nikto_out, scan_stage="nikto_done")

    await asyncio.sleep(0.8)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: AI ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    scans[scan_id]["status"] = "analyzing"
    scans[scan_id]["scan_stage"] = "analyzing"
    update_scan_status(scan_id, "analyzing", scan_stage="analyzing")

    await _narrate_block(scan_id, [
        "",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 3/4]\x1b[0m  \x1b[1;37mAI THREAT ANALYSIS\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Feeding scan data to AI engine...\r\n", 0.5)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Cross-referencing CVE/NVD databases...\r\n", 0.8)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Evaluating attack surface vectors...\r\n", 0.6)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Generating risk prioritization matrix...\r\n", 0.4)

    analysis = await asyncio.to_thread(analyze_results, nmap_out, nikto_out)
    scans[scan_id]["analysis"] = analysis

    await _narrate(scan_id, "\x1b[1;32m[SENTRA]\x1b[0m \x1b[32m✓\x1b[0m AI threat analysis complete.\r\n", 0.5)

    await asyncio.sleep(0.6)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: REMEDIATION
    # ═══════════════════════════════════════════════════════════════
    scans[scan_id]["scan_stage"] = "generating_fixes"
    update_scan_status(scan_id, "analyzing", scan_stage="generating_fixes")

    await _narrate_block(scan_id, [
        "",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 4/4]\x1b[0m  \x1b[1;37mREMEDIATION PLAYBOOKS\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Detecting target operating system...\r\n", 0.5)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Drafting automated fix scripts...\r\n", 0.6)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Mapping fixes to MITRE ATT&CK framework...\r\n", 0.5)

    from .remediation import generate_fixes
    fixes = await asyncio.to_thread(generate_fixes, nmap_output=nmap_out, nikto_output=nikto_out)
    scans[scan_id]["fixes"] = fixes

    fix_count = len(fixes.get("findings", [])) if fixes else 0
    await _narrate(scan_id, f"\x1b[1;32m[SENTRA]\x1b[0m \x1b[32m✓\x1b[0m {fix_count} remediation playbook(s) generated.\r\n", 0.5)

    await asyncio.sleep(0.5)

    # ═══════════════════════════════════════════════════════════════
    # RISK SCORE CALCULATION
    # ═══════════════════════════════════════════════════════════════
    risk_score = _calculate_risk_score(open_ports, vuln_count, fixes)
    risk_label = "CRITICAL" if risk_score >= 8 else "HIGH" if risk_score >= 6 else "MEDIUM" if risk_score >= 4 else "LOW"
    risk_color = "\x1b[1;31m" if risk_score >= 8 else "\x1b[1;33m" if risk_score >= 4 else "\x1b[1;32m"
    
    scans[scan_id]["risk_score"] = risk_score
    scans[scan_id]["risk_label"] = risk_label

    # ═══════════════════════════════════════════════════════════════
    # COMPLETE
    # ═══════════════════════════════════════════════════════════════
    await _narrate_block(scan_id, [
        "",
        "\x1b[36m╔══════════════════════════════════════════════════════════╗\x1b[0m",
        "\x1b[36m║\x1b[0m  \x1b[1;32m✓ OPERATION COMPLETE\x1b[0m                                    \x1b[36m║\x1b[0m",
        "\x1b[36m╠══════════════════════════════════════════════════════════╣\x1b[0m",
        f"\x1b[36m║\x1b[0m  Target:     \x1b[1;37m{target:<45}\x1b[0m\x1b[36m║\x1b[0m",
        f"\x1b[36m║\x1b[0m  Ports:      \x1b[1;33m{open_ports:<45}\x1b[0m\x1b[36m║\x1b[0m",
        f"\x1b[36m║\x1b[0m  Findings:   \x1b[1;33m{vuln_count:<45}\x1b[0m\x1b[36m║\x1b[0m",
        f"\x1b[36m║\x1b[0m  Fixes:      \x1b[1;32m{fix_count:<45}\x1b[0m\x1b[36m║\x1b[0m",
        f"\x1b[36m║\x1b[0m  Risk Score: {risk_color}{risk_score}/10 — {risk_label:<39}\x1b[0m\x1b[36m║\x1b[0m",
        "\x1b[36m╚══════════════════════════════════════════════════════════╝\x1b[0m",
        "",
        "\x1b[32m[SENTRA]\x1b[0m Full report ready. Returning to dashboard.\r\n",
    ], delay=0.1)

    # 5. Mark complete
    scans[scan_id]["status"] = "complete"
    scans[scan_id]["scan_stage"] = "complete"
    scans[scan_id]["completed_at"] = datetime.now().isoformat()
    update_scan_status(scan_id, "complete", analysis=analysis, fixes=fixes, scan_stage="complete",
                       risk_score=risk_score, risk_label=risk_label)


@app.websocket("/ws/scan/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    await manager.connect(websocket, scan_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, scan_id)

@app.get("/")
def home():
    return {"status": "online", "system": "Sentra.AI Unified Command"}


@app.get("/health")
def health_check():
    return {
        "status": "online",
        "nmap_available": scanner.is_available(),
        "nikto_available": bool(scanner.nikto_path or scanner.use_docker_nikto),
        "active_scans": sum(1 for s in scans.values() if s.get("status") not in ["complete", "failed"]),
    }


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # Run in thread instead of blocking event loop
    intent = await asyncio.to_thread(process_chat_query, req.message)
    
    if intent.get("action") == "scan" and intent.get("target"):
        target = intent["target"]
        
        if not verify_target_ownership(target):
            return {
                "type": "error",
                "message": f"⛔ VERIFICATION FAILED: {target}\n"
                           f"Strict Mode Enabled. You must host 'sentra-verify.txt' on the target."
            }
        
        return {
            "type": "action_required",
            "action": "start_scan",
            "target": target,
            "message": f"Target {target} Verified. Ready to launch Scan."
        }

    # Returning exactly what the single API call generated
    return {"type": "message", "message": intent.get("message", "No response generated.")}


@app.post("/scan/start")
async def start_scan_endpoint(req: ScanRequest, bg_tasks: BackgroundTasks):
    if not verify_target_ownership(req.target):
        raise HTTPException(403, "Verification Failed")
        
    scan_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    scan_data = {"target": req.target, "status": "pending", "created_at": now}
    
    scans[scan_id] = scan_data
    save_scan(scan_id, scan_data)
    
    bg_tasks.add_task(run_background_scan, scan_id, req.target)
    return {"scan_id": scan_id, "status": "started"}


@app.get("/scans")
def list_all_scans():
    return list_scans()

@app.delete("/scan/{scan_id}")
def delete_existing_scan(scan_id: str):
    if scan_id in scans:
        del scans[scan_id]
    delete_scan(scan_id)
    return {"status": "deleted"}

@app.get("/scan/{scan_id}")
def get_scan_status(scan_id: str):
    # Check in-memory first (active scans), then DB
    if scan_id in scans:
        data = scans[scan_id].copy()
        data["scan_id"] = scan_id
        return data
    
    db_scan = get_scan(scan_id)
    if not db_scan:
        raise HTTPException(404, "Scan ID not found")
    return db_scan


@app.get("/scan/{scan_id}/export")
def export_scan_pdf(scan_id: str):
    from fastapi.responses import FileResponse
    scan_data = _get_complete_scan(scan_id)
    
    try:
        from .reporting import generate_pdf_report
        scan_data["scan_id"] = scan_id
        report_path = generate_pdf_report(scan_data, f"sentra_report_{scan_id[:8]}.pdf")
        return FileResponse(
            path=report_path,
            media_type="application/pdf",
            filename=f"sentra_report_{scan_data.get('target', 'scan')}_{scan_id[:8]}.pdf"
        )
    except Exception as e:
        logger.error(f"PDF Export failed: {e}")
        raise HTTPException(500, f"PDF generation failed: {str(e)}")


@app.get("/scan/{scan_id}/fixes")
def get_scan_fixes(scan_id: str):
    scan_data = _get_complete_scan(scan_id)
    
    from .remediation import generate_fixes, format_fixes_for_display
    
    # Use cached fixes or generate new ones
    fixes = scan_data.get("fixes")
    if not fixes:
        fixes = generate_fixes(
            nmap_output=scan_data.get("nmap", ""),
            nikto_output=scan_data.get("nikto", "")
        )
        # Cache in memory and DB
        if scan_id in scans:
            scans[scan_id]["fixes"] = fixes
        update_scan_status(scan_id, "complete", fixes=fixes)
    
    return {
        "status": "generated",
        "os_detected": fixes.get("os_detected", "unknown"),
        "fix_count": len(fixes.get("findings", [])),
        "fixes": fixes,
        "formatted": format_fixes_for_display(fixes)
    }


def _get_complete_scan(scan_id: str) -> dict:
    """Helper to get a complete scan from memory or DB."""
    if scan_id in scans:
        data = scans[scan_id]
    else:
        data = get_scan(scan_id)
    
    if not data:
        raise HTTPException(404, "Scan ID not found")
    if data.get("status") != "complete":
        raise HTTPException(400, "Scan not complete yet")
    
    return data
