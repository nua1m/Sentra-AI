import asyncio
import logging
import sys
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Windows requires ProactorEventLoop for subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import contextlib
from datetime import datetime

from .database import delete_scan, get_scan, list_scans, save_scan, update_scan_status
from .intelligence import ask_kimi, chat_with_context, process_chat_query, select_tools
from .security import verify_target_ownership
from .tools import TOOL_REGISTRY, get_available_tools, get_tool

# Setup
app = FastAPI(title="Sentra.AI Core")
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
scans: dict[str, dict] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.scan_logs: dict[str, list[str]] = {}

    async def connect(self, websocket: WebSocket, scan_id: str):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)

        # Send history
        if scan_id in self.scan_logs:
            for line in self.scan_logs[scan_id]:
                with contextlib.suppress(Exception):
                    await websocket.send_text(line)

    def disconnect(self, websocket: WebSocket, scan_id: str):
        if scan_id in self.active_connections and websocket in self.active_connections[scan_id]:
            self.active_connections[scan_id].remove(websocket)

    async def broadcast(self, message: str, scan_id: str):
        if scan_id not in self.scan_logs:
            self.scan_logs[scan_id] = []
        self.scan_logs[scan_id].append(message)

        if scan_id in self.active_connections:
            for connection in self.active_connections[scan_id]:
                with contextlib.suppress(Exception):
                    await connection.send_text(message)

manager = ConnectionManager()


class ChatRequest(BaseModel):
    message: str

class ScanRequest(BaseModel):
    target: str
    requested_tools: list[str] | None = None  # e.g. ["nmap"] for nmap-only


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


async def run_background_scan(scan_id: str, target: str, requested_tools: list[str] | None = None):
    scans[scan_id]["status"] = "scanning"
    scans[scan_id]["scan_stage"] = "nmap_running"
    scans[scan_id]["tools_used"] = ["nmap"]  # Track which tools ran
    if requested_tools:
        scans[scan_id]["requested_tools"] = requested_tools
    update_scan_status(scan_id, "scanning", scan_stage="nmap_running")

    # Grab tools from registry
    nmap_tool = get_tool("nmap")
    available_followups = [t for t in get_available_tools() if t.name != "nmap"]

    # ═══════════════════════════════════════════════════════════════
    # PHASE 0: BOOT SEQUENCE
    # ═══════════════════════════════════════════════════════════════
    tool_list_lines = []
    for t in TOOL_REGISTRY:
        status = "\x1b[32m✓\x1b[0m" if t.is_available() else "\x1b[31m✗\x1b[0m"
        tool_list_lines.append(f"\x1b[32m[SENTRA]\x1b[0m  {status} {t.label} ({t.name})")

    await _narrate_block(scan_id, [
        "",
        "\x1b[36m╔══════════════════════════════════════════════════════════╗\x1b[0m",
        "\x1b[36m║\x1b[0m  \x1b[1;37mSENTRA AI — Autonomous Security Assessment Engine\x1b[0m      \x1b[36m║\x1b[0m",
        "\x1b[36m║\x1b[0m  \x1b[90mv3.0.0 | Intelligent Agent Pipeline\x1b[0m                    \x1b[36m║\x1b[0m",
        "\x1b[36m╚══════════════════════════════════════════════════════════╝\x1b[0m",
        "",
    ], delay=0.08)

    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Target acquired: \x1b[1;37m{target}\x1b[0m\r\n", 0.4)
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Session ID: \x1b[90m{scan_id}\x1b[0m\r\n", 0.3)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Verifying target ownership... ", 0.6)
    await _narrate(scan_id, "\x1b[1;32m✓ VERIFIED\x1b[0m\r\n", 0.5)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Loading tool registry...\r\n", 0.4)
    for line in tool_list_lines:
        await _narrate(scan_id, line + "\r\n", 0.12)
    await _narrate(scan_id, "\r\n", 0.3)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: NMAP (always runs first)
    # ═══════════════════════════════════════════════════════════════
    await _narrate_block(scan_id, [
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 1]\x1b[0m  \x1b[1;37mNETWORK RECONNAISSANCE\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Executing: \x1b[33mnmap -F -T4 {target}\x1b[0m\r\n", 0.3)
    await _narrate(scan_id, "\r\n", 0.2)

    nmap_lines = []
    async for line in nmap_tool.run_stream(target):
        nmap_lines.append(line)
        formatted_line = line.replace('\n', '\r\n') if not line.endswith('\r\n') else line
        await manager.broadcast(formatted_line, scan_id)
        await asyncio.sleep(0.04)
    nmap_out = "".join(nmap_lines)

    # Extract open port numbers
    open_port_lines = [line for line in nmap_lines if '/tcp' in line and 'open' in line]
    open_ports_count = len(open_port_lines)
    import re
    open_port_numbers = []
    for line in open_port_lines:
        m = re.match(r'(\d+)/tcp', line.strip())
        if m:
            open_port_numbers.append(m.group(1))

    await _narrate(scan_id, "\r\n", 0.2)
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Network scan complete. \x1b[1;33m{open_ports_count} open port(s)\x1b[0m detected.", 0.3)
    if open_port_numbers:
        await _narrate(scan_id, f" Ports: \x1b[1;37m{', '.join(open_port_numbers)}\x1b[0m\r\n", 0.3)
    else:
        await _narrate(scan_id, "\r\n", 0.2)

    scans[scan_id]["nmap"] = nmap_out
    scans[scan_id]["scan_stage"] = "nmap_done"
    update_scan_status(scan_id, "scanning", nmap=nmap_out, scan_stage="nmap_done")

    await asyncio.sleep(0.8)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: AI TOOL SELECTION + DYNAMIC TOOL EXECUTION
    # ═══════════════════════════════════════════════════════════════
    await _narrate_block(scan_id, [
        "",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 2]\x1b[0m  \x1b[1;37mINTELLIGENT TOOL SELECTION\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m AI agent analyzing Nmap findings...\r\n", 0.5)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Evaluating which tools are relevant for this target...\r\n", 0.6)

    # Build tool info for AI
    tool_info = [
        {"name": t.name, "description": t.description, "ports": t.relevant_ports}
        for t in available_followups
    ]

    # AI decides which tools to run (SKIP if user requested specific tools)
    only_nmap = requested_tools and requested_tools == ["nmap"]
    if only_nmap:
        selected_names = []
        selected_tools = []
        await _narrate(scan_id, "\x1b[33m[AGENT]\x1b[0m User requested Nmap only — skipping follow-up tools.\r\n", 0.4)
    else:
        selected_names = await asyncio.to_thread(select_tools, nmap_out, tool_info)
        selected_tools = [t for t in available_followups if t.name in selected_names]

    if selected_tools:
        await _narrate(scan_id, f"\x1b[1;33m[AGENT]\x1b[0m Selected \x1b[1;37m{len(selected_tools)}\x1b[0m follow-up tool(s):\r\n", 0.4)
        for t in selected_tools:
            await _narrate(scan_id, f"\x1b[33m[AGENT]\x1b[0m  → {t.label} ({t.name})\r\n", 0.2)
    else:
        await _narrate(scan_id, "\x1b[33m[AGENT]\x1b[0m No follow-up tools needed for this target.\r\n", 0.4)

    await asyncio.sleep(0.5)

    # Collect all tool outputs
    all_outputs = {"nmap": nmap_out}
    nikto_out = ""
    vuln_count = 0

    # Run each selected tool
    for idx, tool in enumerate(selected_tools):
        tool_num = idx + 1
        scans[scan_id]["scan_stage"] = f"{tool.name}_running"
        scans[scan_id]["tools_used"].append(tool.name)
        update_scan_status(scan_id, "scanning", scan_stage=f"{tool.name}_running")

        await _narrate_block(scan_id, [
            "",
            "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
            f"\x1b[1;36m  [TOOL {tool_num}/{len(selected_tools)}]\x1b[0m  \x1b[1;37m{tool.label.upper()}\x1b[0m",
            "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
            "",
        ], delay=0.1)

        await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Executing: \x1b[33m{tool.name} → {target}\x1b[0m\r\n", 0.3)
        await _narrate(scan_id, "\r\n", 0.2)

        tool_lines = []
        async for line in tool.run_stream(target):
            tool_lines.append(line)
            formatted_line = line.replace('\n', '\r\n') if not line.endswith('\r\n') else line
            await manager.broadcast(formatted_line, scan_id)
            await asyncio.sleep(0.04)

        tool_output = "".join(tool_lines)
        all_outputs[tool.name] = tool_output

        # Store in scan data
        scans[scan_id][tool.name] = tool_output

        # Track nikto-specific stats
        if tool.name == "nikto":
            nikto_out = tool_output
            vuln_count = sum(1 for line in tool_lines if line.strip().startswith('+') or 'OSVDB' in line)

        finding_count = len(tool_lines)
        await _narrate(scan_id, "\r\n", 0.2)
        await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m {tool.label} complete. \x1b[1;33m{finding_count} line(s)\x1b[0m of output.\r\n", 0.4)

        scans[scan_id]["scan_stage"] = f"{tool.name}_done"
        update_scan_status(scan_id, "scanning", scan_stage=f"{tool.name}_done")
        await asyncio.sleep(0.5)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: AI ANALYSIS (fed ALL tool outputs)
    # ═══════════════════════════════════════════════════════════════
    scans[scan_id]["status"] = "analyzing"
    scans[scan_id]["scan_stage"] = "analyzing"
    update_scan_status(scan_id, "analyzing", scan_stage="analyzing")

    await _narrate_block(scan_id, [
        "",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "\x1b[1;36m  [PHASE 3]\x1b[0m  \x1b[1;37mAI THREAT ANALYSIS\x1b[0m",
        "\x1b[36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\x1b[0m",
        "",
    ], delay=0.1)

    tools_used = scans[scan_id]["tools_used"]
    await _narrate(scan_id, f"\x1b[32m[SENTRA]\x1b[0m Feeding data from {len(tools_used)} tool(s) to AI engine...\r\n", 0.5)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Cross-referencing CVE/NVD databases...\r\n", 0.8)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Evaluating attack surface vectors...\r\n", 0.6)
    await _narrate(scan_id, "\x1b[32m[SENTRA]\x1b[0m Generating risk prioritization matrix...\r\n", 0.4)

    # Build combined output for AI analysis
    combined_nikto = all_outputs.get("nikto", "No web scan performed.")
    extra_context = ""
    for tool_name, output in all_outputs.items():
        if tool_name not in ("nmap", "nikto"):
            extra_context += f"\n=== {tool_name.upper()} RESULTS ===\n{output[:2000]}\n"

    # Extend the analysis prompt with extra tool data
    analysis_prompt = f"""
    Analyze these security scan results and provide a concise assessment.
    Tools used: {', '.join(tools_used)}

    === NMAP SCAN ===
    {nmap_out[:3000]}

    === NIKTO WEB SCAN ===
    {combined_nikto[:3000]}
    {extra_context}
    Format as:
    1. **Summary**: What is running?
    2. **Risks**: Potential vulnerabilities (if any obvious versions).
    3. **Recommendations**: Basic hardening steps.
    """
    analysis = await asyncio.to_thread(ask_kimi, analysis_prompt)
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
        "\x1b[1;36m  [PHASE 4]\x1b[0m  \x1b[1;37mREMEDIATION PLAYBOOKS\x1b[0m",
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
    risk_score = _calculate_risk_score(open_ports_count, vuln_count, fixes)
    risk_label = "CRITICAL" if risk_score >= 8 else "HIGH" if risk_score >= 6 else "MEDIUM" if risk_score >= 4 else "LOW"
    risk_color = "\x1b[1;31m" if risk_score >= 8 else "\x1b[1;33m" if risk_score >= 4 else "\x1b[1;32m"

    scans[scan_id]["risk_score"] = risk_score
    scans[scan_id]["risk_label"] = risk_label

    # ═══════════════════════════════════════════════════════════════
    # COMPLETE
    # ═══════════════════════════════════════════════════════════════
    tools_str = ', '.join(tools_used)
    await _narrate_block(scan_id, [
        "",
        "\x1b[36m╔══════════════════════════════════════════════════════════╗\x1b[0m",
        "\x1b[36m║\x1b[0m  \x1b[1;32m✓ OPERATION COMPLETE\x1b[0m                                    \x1b[36m║\x1b[0m",
        "\x1b[36m╠══════════════════════════════════════════════════════════╣\x1b[0m",
        f"\x1b[36m║\x1b[0m  Target:     \x1b[1;37m{target:<45}\x1b[0m\x1b[36m║\x1b[0m",
        f"\x1b[36m║\x1b[0m  Tools:      \x1b[1;37m{tools_str:<45}\x1b[0m\x1b[36m║\x1b[0m",
        f"\x1b[36m║\x1b[0m  Ports:      \x1b[1;33m{open_ports_count:<45}\x1b[0m\x1b[36m║\x1b[0m",
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
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, scan_id)

@app.get("/")
def home():
    return {"status": "online", "system": "Sentra.AI Unified Command"}


@app.get("/health")
def health_check():
    tools_status = {t.name + "_available": t.is_available() for t in TOOL_REGISTRY}
    return {
        "status": "online",
        **tools_status,
        "active_scans": sum(1 for s in scans.values() if s.get("status") not in ["complete", "failed"]),
    }


class ChatRequest2(BaseModel):
    message: str
    scan_id: str = None

@app.post("/chat")
async def chat_endpoint(req: ChatRequest2):
    # If scan_id is provided, use contextual chat
    if req.scan_id:
        scan_data = None
        scan_data = scans[req.scan_id] if req.scan_id in scans else get_scan(req.scan_id)

        if scan_data and scan_data.get("status") == "complete":
            response = await asyncio.to_thread(
                chat_with_context, req.message, req.scan_id, scan_data
            )
            return {"type": "message", "message": response}

    # Standard intent classification
    intent = await asyncio.to_thread(process_chat_query, req.message)

    if intent.get("action") == "scan" and intent.get("target"):
        target = intent["target"]
        tools = intent.get("tools")  # e.g. ["nmap"] if user said "run nmap"

        if not verify_target_ownership(target):
            return {
                "type": "error",
                "message": f"⛔ VERIFICATION FAILED: {target}\n"
                           f"Strict Mode Enabled. You must host 'sentra-verify.txt' on the target."
            }

        result = {
            "type": "action_required",
            "action": "start_scan",
            "target": target,
            "message": f"Target {target} Verified. Ready to launch Scan."
        }
        if tools:
            result["requested_tools"] = tools
        return result

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

    bg_tasks.add_task(run_background_scan, scan_id, req.target, req.requested_tools)
    return {"scan_id": scan_id, "status": "started"}


@app.get("/scans")
def list_all_scans():
    return list_scans()

@app.delete("/scan/{scan_id}")
def delete_existing_scan(scan_id: str):
    scans.pop(scan_id, None)
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
        raise HTTPException(500, f"PDF generation failed: {e!s}")


@app.get("/scan/{scan_id}/fixes")
def get_scan_fixes(scan_id: str):
    scan_data = _get_complete_scan(scan_id)

    from .remediation import format_fixes_for_display, generate_fixes

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
    data = scans[scan_id] if scan_id in scans else get_scan(scan_id)

    if not data:
        raise HTTPException(404, "Scan ID not found")
    if data.get("status") != "complete":
        raise HTTPException(400, "Scan not complete yet")

    return data
