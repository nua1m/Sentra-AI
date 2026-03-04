import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.security import verify_api_key
from api.models.schemas import ScanOut, ScanRequest, ScanSummaryOut
from api.services.agent0_client import Agent0Client, get_agent0_client
from api.services import scan_service

router = APIRouter(prefix="/api/v1/scans", tags=["scans"])


@router.post("", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
async def start_scan(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db),
    agent0: Agent0Client = Depends(get_agent0_client),
    _: str = Depends(verify_api_key),
) -> ScanOut:
    """Start a security scan on a target. Blocks until the scan completes."""
    scan = await scan_service.create_scan(
        db=db,
        agent0=agent0,
        target=request.target,
        scan_type=request.scan_type,
    )
    return _to_scan_out(scan)


@router.get("", response_model=list[ScanSummaryOut])
async def list_scans(
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> list[ScanSummaryOut]:
    """List all scan sessions, newest first. No findings payload (use GET /{id})."""
    scans = await scan_service.list_scans(db, offset=offset, limit=min(limit, 100))
    return [_to_summary_out(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> ScanOut:
    """Get a single scan with all its findings."""
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
    """Delete a scan and all its findings."""
    deleted = await scan_service.delete_scan(db, scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scan not found")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_scan_out(scan) -> ScanOut:
    tools = json.loads(scan.tools_used) if scan.tools_used else []
    return ScanOut(
        id=scan.id,
        target=scan.target,
        status=scan.status,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        tools_used=tools,
        summary=scan.summary,
        findings=[_f(f) for f in (scan.findings or [])],
        created_at=scan.created_at,
    )


def _to_summary_out(scan) -> ScanSummaryOut:
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


def _f(f) -> dict:
    return {
        "id": f.id,
        "severity": f.severity,
        "title": f.title,
        "tool": f.tool,
        "cve": f.cve,
        "cvss": f.cvss,
        "remediation": f.remediation,
        "created_at": f.created_at,
    }
