import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ─── Request schemas ─────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=255)
    scan_type: str = Field(default="full", pattern="^(full|quick|web|ports)$")


# ─── Response schemas ─────────────────────────────────────────────────────────

class ScanStarted(BaseModel):
    """Returned immediately when a scan is accepted (202)."""
    scan_id: uuid.UUID
    status: str  # "pending"
    stream_url: str  # e.g. /api/v1/scans/{id}/stream


class FindingOut(BaseModel):
    id: uuid.UUID
    severity: str
    title: str
    tool: str | None
    cve: str | None
    cvss: float | None
    remediation: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanOut(BaseModel):
    id: uuid.UUID
    target: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    tools_used: list[str] | None
    summary: str | None
    findings: list[FindingOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanSummaryOut(BaseModel):
    id: uuid.UUID
    target: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    summary: str | None
    finding_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthOut(BaseModel):
    status: str
    agent0: str
    database: str
