import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.core.config import get_settings
from api.models.db import Finding, ScanSession
from api.services.agent0_client import Agent0Client

VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
settings = get_settings()

SCAN_STRATEGIES = {
    "quick": "Run one quick host/service discovery pass only.",
    "ports": "Focus on port exposure only.",
    "web": "Focus on web-surface checks only.",
    "full": "Run one comprehensive network security assessment pass.",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _scan_timeout(scan_type: str) -> int:
    if scan_type in {"quick", "ports", "web"}:
        return settings.quick_scan_timeout_seconds
    return settings.scan_timeout_seconds


async def fail_stale_running_scans(db: AsyncSession) -> int:
    cutoff = _utcnow().timestamp() - settings.stale_scan_timeout_seconds
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
    result = await db.execute(
        select(ScanSession).where(
            ScanSession.status == "running",
            ScanSession.started_at < cutoff_dt,
        )
    )
    stale = list(result.scalars().all())
    for scan in stale:
        scan.status = "failed"
        scan.error = "Scan exceeded maximum runtime"
        scan.completed_at = _utcnow()

    if stale:
        await db.commit()
    return len(stale)


async def create_pending_scan(db: AsyncSession, target: str, scan_type: str) -> ScanSession:
    """Create a scan record immediately and return it — scan runs in background."""
    scan = ScanSession(
        target=target,
        status="pending",
        started_at=_utcnow(),
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def run_scan(
    db: AsyncSession,
    agent0: Agent0Client,
    scan_id: uuid.UUID,
    target: str,
    scan_type: str = "full",
) -> None:
    """Background task: run the full scan and persist results.
    Updates scan status throughout: pending → running → completed/failed.
    """
    scan = await db.get(ScanSession, scan_id)
    if not scan:
        return

    try:
        # Mark running
        scan.status = "running"
        await db.commit()

        # ── Call 1: run the audit and return structured JSON ────────────
        strategy = SCAN_STRATEGIES.get(scan_type, SCAN_STRATEGIES["full"])
        prompt = (
            f"Target: {target}. Scan mode: {scan_type}. {strategy} "
            "Use only the minimum required commands, avoid retries/loops, and finish in a single run. "
            "Return ONLY one valid JSON object (no markdown, no extra text) with this schema: "
            '{"target":"string","scan_date":"ISO-8601","tools_used":["string"],'
            '"findings":[{"severity":"critical|high|medium|low|info","title":"string",'
            '"tool":"string|null","cve":"CVE-XXXX-XXXX|null","cvss":0-10|null,'
            '"remediation":"string|null"}],"summary":"string"}'
        )
        result = await agent0.send_message(prompt, timeout=_scan_timeout(scan_type))
        context_id: str | None = result.get("context_id")
        raw_report: str = (
            result.get("text")
            or result.get("message")
            or result.get("response")
            or ""
        )

        # Persist context_id so SSE endpoint can stream logs
        scan.context_id = context_id
        await db.commit()

        # ── Parse JSON from first call, then fallback to second call ────
        findings_data: list[dict] = []
        summary: str | None = None
        tools_used: list[str] = []

        json_result = agent0.parse_scan_json(raw_report)
        if not json_result and context_id:
            json_result = await agent0.extract_json(context_id)

        if json_result:
            tools_used = json_result.get("tools_used", [])
            summary = json_result.get("summary")
            findings_data = json_result.get("findings", [])

        # ── Persist findings ─────────────────────────────────────────────
        for f in findings_data:
            severity = f.get("severity", "info").lower()
            if severity not in VALID_SEVERITIES:
                severity = "info"

            cvss_raw = f.get("cvss")
            cvss = float(cvss_raw) if cvss_raw is not None else None

            cve = f.get("cve") or None
            if cve and not cve.upper().startswith("CVE-"):
                cve = None

            db.add(Finding(
                scan_id=scan.id,
                severity=severity,
                title=str(f.get("title", "Unknown finding"))[:500],
                tool=f.get("tool"),
                cve=cve,
                cvss=cvss,
                remediation=f.get("remediation"),
            ))

        scan.status = "completed"
        scan.completed_at = _utcnow()
        scan.raw_report = raw_report[:50_000]
        scan.summary = summary
        scan.tools_used = json.dumps(tools_used) if tools_used else None
        await db.commit()

    except Exception as exc:
        scan.status = "failed"
        scan.error = str(exc)[:500]
        scan.completed_at = _utcnow()
        await db.commit()
        raise


async def get_scan(db: AsyncSession, scan_id: uuid.UUID) -> ScanSession | None:
    result = await db.execute(
        select(ScanSession)
        .where(ScanSession.id == scan_id)
        .options(selectinload(ScanSession.findings))
    )
    return result.scalar_one_or_none()


async def list_scans(db: AsyncSession, offset: int = 0, limit: int = 20) -> list[ScanSession]:
    result = await db.execute(
        select(ScanSession)
        .order_by(ScanSession.created_at.desc())
        .options(selectinload(ScanSession.findings))
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_scan(db: AsyncSession, scan_id: uuid.UUID) -> bool:
    scan = await db.get(ScanSession, scan_id)
    if not scan:
        return False
    await db.delete(scan)
    await db.commit()
    return True
