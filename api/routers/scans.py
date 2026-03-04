import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import AsyncSessionLocal, get_db
from api.core.security import verify_api_key
from api.models.schemas import ScanOut, ScanRequest, ScanStarted, ScanSummaryOut
from api.services import scan_service
from api.services.agent0_client import Agent0Client, get_agent0_client

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])
logger = logging.getLogger(__name__)


# ─── Start scan (async, returns 202 immediately) ─────────────────────────────

@router.post("", response_model=ScanStarted, status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db),
    agent0: Agent0Client = Depends(get_agent0_client),
    _: str = Depends(verify_api_key),
) -> ScanStarted:
    """Accepts a scan request and returns immediately. Poll /stream for live output."""
    await scan_service.fail_stale_running_scans(db)
    scan = await scan_service.create_pending_scan(db, request.target, request.scan_type)

    # Run in background — uses its own DB session
    asyncio.create_task(_run_scan_task(scan.id, request.target, request.scan_type))

    return ScanStarted(
        scan_id=scan.id,
        status="pending",
        stream_url=f"/api/v1/scans/{scan.id}/stream",
    )


async def _run_scan_task(scan_id: uuid.UUID, target: str, scan_type: str) -> None:
    """Background task wrapper — creates its own DB session."""
    async with AsyncSessionLocal() as db:
        agent0 = Agent0Client()
        try:
            healthy = await agent0.check_health()
            if not healthy:
                logger.error("Agent0 unreachable before scan %s", scan_id)
            await scan_service.run_scan(db, agent0, scan_id, target, scan_type)
        except Exception:
            logger.exception("Background scan task failed for %s", scan_id)


# ─── SSE live stream ─────────────────────────────────────────────────────────

@router.get("/{scan_id}/stream")
async def stream_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    agent0: Agent0Client = Depends(get_agent0_client),
    _: str = Depends(verify_api_key),
) -> StreamingResponse:
    """Server-Sent Events stream of live Agent0 output for this scan."""

    async def event_generator():
        seen = 0
        while True:
            scan = await scan_service.get_scan(db, scan_id)
            if not scan:
                yield _sse("error", "Scan not found")
                break

            # Stream new log lines if we have a context_id
            if scan.context_id:
                log_data = await agent0.get_log(scan.context_id, start=seen)
                items = log_data.get("items", [])
                for item in items:
                    line = item.get("content") or item.get("text") or ""
                    if line:
                        yield _sse("log", line)
                seen += len(items)

            if scan.status == "completed":
                # Send structured findings as the final event
                findings_payload = [
                    {
                        "id": str(f.id),
                        "severity": f.severity,
                        "title": f.title,
                        "tool": f.tool,
                        "cve": f.cve,
                        "cvss": f.cvss,
                        "remediation": f.remediation,
                    }
                    for f in (scan.findings or [])
                ]
                yield _sse("complete", json.dumps({
                    "scan_id": str(scan.id),
                    "target": scan.target,
                    "summary": scan.summary,
                    "findings": findings_payload,
                }))
                break

            if scan.status == "failed":
                yield _sse("error", scan.error or "Scan failed")
                break

            # Still running — keep polling
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


def _sse(event: str, data: str) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {data}\n\n"


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ScanSummaryOut])
async def list_scans(
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> list[ScanSummaryOut]:
    scans = await scan_service.list_scans(db, offset=offset, limit=min(limit, 100))
    return [_to_summary(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> ScanOut:
    scan = await scan_service.get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _to_scan_out(scan)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> None:
    if not await scan_service.delete_scan(db, scan_id):
        raise HTTPException(status_code=404, detail="Scan not found")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_scan_out(scan) -> ScanOut:
    try:
        tools = json.loads(scan.tools_used) if scan.tools_used else []
    except (TypeError, json.JSONDecodeError):
        tools = []

    return ScanOut(
        id=scan.id,
        target=scan.target,
        status=scan.status,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        tools_used=tools,
        summary=scan.summary,
        error=scan.error,
        findings=[{
            "id": f.id,
            "severity": f.severity,
            "title": f.title,
            "tool": f.tool,
            "cve": f.cve,
            "cvss": f.cvss,
            "remediation": f.remediation,
            "created_at": f.created_at,
        } for f in (scan.findings or [])],
        created_at=scan.created_at,
    )


def _to_summary(scan) -> ScanSummaryOut:
    return ScanSummaryOut(
        id=scan.id,
        target=scan.target,
        status=scan.status,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        summary=scan.summary,
        finding_count=len(scan.findings) if scan.findings else 0,
        created_at=scan.created_at,
    )
