from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import logging
import uuid
from typing import Dict

from .security import verify_target_ownership
from .scanner import Scanner
from .intelligence import classify_intent, ask_kimi, analyze_results

# Setup
app = FastAPI(title="Sentra.AI Core")
scanner = Scanner()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentra.main")

# In-memory session store (for PoC)
# scans[scan_id] = { status, output, analysis }
scans: Dict[str, dict] = {}

class ChatRequest(BaseModel):
    message: str

class ScanRequest(BaseModel):
    target: str

async def run_background_scan(scan_id: str, target: str):
    scans[scan_id]["status"] = "scanning"
    
    # 1. Run Nmap
    nmap_out = await scanner.run_nmap_scan(target)
    scans[scan_id]["nmap"] = nmap_out
    
    # 2. Analyze
    scans[scan_id]["status"] = "analyzing"
    analysis = analyze_results(nmap_out)
    scans[scan_id]["analysis"] = analysis
    
    scans[scan_id]["status"] = "complete"

@app.get("/")
def home():
    return {"status": "online", "system": "Sentra.AI Unified Command"}

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Intelligent CLI Endpoint.
    Decides if we need to scan or just chat.
    """
    intent = classify_intent(req.message)
    
    if intent.get("action") == "scan" and intent.get("target"):
        target = intent["target"]
        
        # SECURITY CHECK (Option A Compliance)
        if not verify_target_ownership(target):
            return {
                "type": "error",
                "message": f"⛔ VERIFICATION FAILED: {target}\n"
                           f"Strict Mode Enabled. You must host 'sentra-verify.txt' on the target."
            }
        
        # Start Scan
        scan_id = str(uuid.uuid4())
        scans[scan_id] = {"target": target, "status": "pending"}
        
        # We trigger the scan via background task? 
        # For simplicity in CLI flow, we might return the ID and let CLI poll status, 
        # or we trigger it here. Ideally BackgroundTasks.
        # But we need to use `BackgroundTasks` in signature.
        # For this turn, we return a special instructions to "start_scan" logic
        
        return {
            "type": "action_required",
            "action": "start_scan",
            "target": target,
            "message": f"Target {target} Verified. Ready to launch Scan."
        }

    # Default Chat
    response = ask_kimi(req.message)
    return {"type": "message", "message": response}

@app.post("/scan/start")
async def start_scan_endpoint(req: ScanRequest, bg_tasks: BackgroundTasks):
    # Double check verification (Security in Depth)
    if not verify_target_ownership(req.target):
        raise HTTPException(403, "Verification Failed")
        
    scan_id = str(uuid.uuid4())
    scans[scan_id] = {"target": req.target, "status": "pending"}
    
    bg_tasks.add_task(run_background_scan, scan_id, req.target)
    return {"scan_id": scan_id, "status": "started"}

@app.get("/scan/{scan_id}")
def get_scan_status(scan_id: str):
    if scan_id not in scans:
        raise HTTPException(404, "Scan ID not found")
    return scans[scan_id]
