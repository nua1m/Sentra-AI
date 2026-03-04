import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.db import Finding, ScanSession
from api.services.agent0_client import Agent0Client

VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_scan(
    db: AsyncSession,
    agent0: Agent0Client,
    target: str,
    scan_type: str = "full",
) -> ScanSession:
    """Orchestrate a full scan: call Agent0, extract JSON, persist to DB."""

    # Create a scan record in 'running' state
    scan = ScanSession(target=target, status="running", started_at=_utcnow())
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    try:
        # ── Call 1: run the full audit ──────────────────────────────────────
        result = await agent0.run_scan(target, scan_type)
        context_id: str | None = result.get("context_id")
        raw_report: str = result.get("text") or result.get("message") or ""

        # ── Call 2: extract structured JSON ─────────────────────────────────
        findings_data: list[dict] = []
        summary: str | None = None
        tools_used: list[str] = []

        if context_id:
            json_result = await agent0.extract_json(context_id)
            if json_result:
                tools_used = json_result.get("tools_used", [])
                summary = json_result.get("summary")
                findings_data = json_result.get("findings", [])

        # ── Persist findings ─────────────────────────────────────────────────
        for f in findings_data:
            severity = f.get("severity", "info").lower()
            if severity not in VALID_SEVERITIES:
                severity = "info"

            cvss_raw = f.get("cvss")
            cvss = float(cvss_raw) if cvss_raw is not None else None

            cve = f.get("cve") or None
            if cve and not cve.upper().startswith("CVE-"):
                cve = None  # Reject malformed CVE strings

            finding = Finding(
                scan_id=scan.id,
                severity=severity,
                title=str(f.get("title", "Unknown finding"))[:500],
                tool=f.get("tool"),
                cve=cve,
                cvss=cvss,
                remediation=f.get("remediation"),
            )
            db.add(finding)

        # ── Update scan record ───────────────────────────────────────────────
        scan.status = "completed"
        scan.completed_at = _utcnow()
        scan.raw_report = raw_report[:50_000]  # Guard against huge reports
        scan.summary = summary
        scan.tools_used = json.dumps(tools_used) if tools_used else None

        await db.commit()
        await db.refresh(scan)

    except Exception as exc:
        scan.status = "failed"
        scan.completed_at = _utcnow()
        await db.commit()
        raise exc

    return await get_scan(db, scan.id)


async def get_scan(db: AsyncSession, scan_id: uuid.UUID) -> ScanSession | None:
    result = await db.execute(
        select(ScanSession)
        .where(ScanSession.id == scan_id)
        .options(selectinload(ScanSession.findings))
    )
    return result.scalar_one_or_none()


async def list_scans(
    db: AsyncSession, offset: int = 0, limit: int = 20
) -> list[ScanSession]:
    result = await db.execute(
        select(ScanSession)
        .order_by(ScanSession.created_at.desc())
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
