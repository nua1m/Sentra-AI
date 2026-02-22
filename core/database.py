"""
Sentra.AI Database Module
SQLite persistence for scan results.
"""
import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("sentra.database")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scans.db")

def delete_scan(scan_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            target TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            scan_stage TEXT,
            nmap TEXT,
            nikto TEXT,
            analysis TEXT,
            fixes TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    # Migration for existing DB
    try:
        conn.execute("ALTER TABLE scans ADD COLUMN scan_stage TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def save_scan(scan_id: str, data: dict):
    conn = sqlite3.connect(DB_PATH)
    fixes_json = json.dumps(data.get("fixes")) if data.get("fixes") else None
    
    conn.execute("""
        INSERT INTO scans (id, target, status, scan_stage, nmap, nikto, analysis, fixes, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            scan_stage=excluded.scan_stage,
            nmap=excluded.nmap,
            nikto=excluded.nikto,
            analysis=excluded.analysis,
            fixes=excluded.fixes,
            completed_at=excluded.completed_at
    """, (
        scan_id,
        data.get("target", ""),
        data.get("status", "pending"),
        data.get("scan_stage"),
        data.get("nmap"),
        data.get("nikto"),
        data.get("analysis"),
        fixes_json,
        data.get("created_at", datetime.now().isoformat()),
        data.get("completed_at")
    ))
    conn.commit()
    conn.close()


def get_scan(scan_id: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    
    if not row:
        return None
    
    return _row_to_dict(row)


def list_scans(limit: int = 50) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM scans ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    
    return [_row_to_dict(r) for r in rows]


def update_scan_status(scan_id: str, status: str, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    updates = ["status = ?"]
    values = [status]
    
    for key in ["scan_stage", "nmap", "nikto", "analysis"]:
        if key in kwargs:
            updates.append(f"{key} = ?")
            values.append(kwargs[key])
    
    if "fixes" in kwargs:
        updates.append("fixes = ?")
        values.append(json.dumps(kwargs["fixes"]))
    
    if status == "complete":
        updates.append("completed_at = ?")
        values.append(datetime.now().isoformat())
    
    values.append(scan_id)
    conn.execute(f"UPDATE scans SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("fixes"):
        try:
            d["fixes"] = json.loads(d["fixes"])
        except (json.JSONDecodeError, TypeError):
            d["fixes"] = None
    return d


# Auto-init on import
init_db()
