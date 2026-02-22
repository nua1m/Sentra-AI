from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import uuid
from datetime import datetime
from typing import Dict

from .security import verify_target_ownership
from .scanner import Scanner
from .intelligence import classify_intent, ask_kimi, analyze_results
from .database import save_scan, get_scan, list_scans, update_scan_status

# Setup
app = FastAPI(title="Sentra.AI Core")
scanner = Scanner()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentra.main")

# CORS — Allow React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache (mirrors SQLite for active scans)
scans: Dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str

class ScanRequest(BaseModel):
    target: str


async def run_background_scan(scan_id: str, target: str):
    scans[scan_id]["status"] = "scanning"
    scans[scan_id]["scan_stage"] = "nmap_running"
    update_scan_status(scan_id, "scanning", scan_stage="nmap_running")
    
    # 1. Run Nmap
    nmap_out = await scanner.run_nmap_scan(target)
    scans[scan_id]["nmap"] = nmap_out
    scans[scan_id]["scan_stage"] = "nmap_done"
    update_scan_status(scan_id, "scanning", nmap=nmap_out, scan_stage="nmap_done")
    
    # 2. Run Nikto
    scans[scan_id]["scan_stage"] = "nikto_running"
    update_scan_status(scan_id, "scanning", scan_stage="nikto_running") # Should update before running generic wait
    nikto_out = await scanner.run_nikto_scan(target)
    scans[scan_id]["nikto"] = nikto_out
    scans[scan_id]["scan_stage"] = "nikto_done"
    update_scan_status(scan_id, "scanning", nikto=nikto_out, scan_stage="nikto_done")
    
    # 3. AI Analysis
    scans[scan_id]["status"] = "analyzing"
    scans[scan_id]["scan_stage"] = "analyzing"
    update_scan_status(scan_id, "analyzing", scan_stage="analyzing")
    analysis = analyze_results(nmap_out, nikto_out)
    scans[scan_id]["analysis"] = analysis
    
    # 4. Generate fixes
    scans[scan_id]["scan_stage"] = "generating_fixes"
    update_scan_status(scan_id, "analyzing", scan_stage="generating_fixes")
    from .remediation import generate_fixes
    fixes = generate_fixes(nmap_output=nmap_out, nikto_output=nikto_out)
    scans[scan_id]["fixes"] = fixes
    
    # 5. Mark complete
    scans[scan_id]["status"] = "complete"
    scans[scan_id]["scan_stage"] = "complete"
    scans[scan_id]["completed_at"] = datetime.now().isoformat()
    update_scan_status(scan_id, "complete", analysis=analysis, fixes=fixes, scan_stage="complete")


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
    intent = classify_intent(req.message)
    
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

    response = ask_kimi(req.message)
    return {"type": "message", "message": response}


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
    scan_data = _get_complete_scan(scan_id)
    
    try:
        from .reporting import generate_pdf_report
        scan_data["scan_id"] = scan_id
        report_path = generate_pdf_report(scan_data, f"sentra_report_{scan_id[:8]}.pdf")
        return {"status": "generated", "path": report_path}
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
