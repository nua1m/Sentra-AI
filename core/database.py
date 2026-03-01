"""
Sentra.AI Database Module
SQLite persistence for scan results.
"""
import contextlib
import json
import logging
import os
import sqlite3
from datetime import datetime

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
            risk_score REAL,
            risk_label TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            scan_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            risk_score REAL,
            risk_label TEXT,
            tools_used TEXT,
            open_ports TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_target ON scan_memory(target)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            openrouter_api_key TEXT,
            ai_model TEXT
        )
    """)
    # Insert default settings row if it doesn't exist
    conn.execute("""
        INSERT OR IGNORE INTO settings (id, openrouter_api_key, ai_model)
        VALUES (1, '', 'moonshotai/kimi-k2.5')
    """)
    
    # Migration for existing DB
    for col in ["scan_stage TEXT", "risk_score REAL", "risk_label TEXT"]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(f"ALTER TABLE scans ADD COLUMN {col}")
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


def get_scan(scan_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()

    if not row:
        return None

    return _row_to_dict(row)


def list_scans(limit: int = 50) -> list[dict]:
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

    for key in ["scan_stage", "nmap", "nikto", "analysis", "risk_score", "risk_label"]:
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


def get_settings() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return {"openrouter_api_key": "", "ai_model": "moonshotai/kimi-k2.5"}
    return dict(row)


def update_settings(api_key: str, model: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE settings SET openrouter_api_key = ?, ai_model = ? WHERE id = 1",
        (api_key, model)
    )
    conn.commit()
    conn.close()


# Auto-init on import
init_db()
