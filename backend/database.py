"""
SQLite database for projects, conversations, and long-term memory.
All data is stored in ~/VibetaffProjects/.vibetaff.db
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_ROOT = Path.home() / "VibetaffProjects"
DB_PATH = PROJECTS_ROOT / ".vibetaff.db"

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT DEFAULT '',
            messages_json TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS memory (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE INDEX IF NOT EXISTS idx_conv_project ON conversations(project_id);
        CREATE INDEX IF NOT EXISTS idx_memory_project ON memory(project_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_key ON memory(project_id, key);
    """)
    conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Projects ────────────────────────────────────────────────

def ensure_project(project_id: str, name: str | None = None) -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row:
        return dict(row)
    project = {
        "id": project_id,
        "name": name or project_id,
        "created_at": _now(),
    }
    conn.execute(
        "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
        (project["id"], project["name"], project["created_at"]),
    )
    conn.commit()
    return project


# ─── Conversations ───────────────────────────────────────────

def create_conversation(project_id: str, title: str = "") -> str:
    ensure_project(project_id)
    conn = _get_conn()
    conv_id = str(uuid.uuid4())
    now = _now()
    conn.execute(
        "INSERT INTO conversations (id, project_id, title, messages_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (conv_id, project_id, title, "[]", now, now),
    )
    conn.commit()
    return conv_id


def save_conversation(conv_id: str, messages: list[dict], title: str | None = None):
    conn = _get_conn()
    now = _now()
    if title is not None:
        conn.execute(
            "UPDATE conversations SET messages_json = ?, title = ?, updated_at = ? WHERE id = ?",
            (json.dumps(messages, ensure_ascii=False), title, now, conv_id),
        )
    else:
        conn.execute(
            "UPDATE conversations SET messages_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(messages, ensure_ascii=False), now, conv_id),
        )
    conn.commit()


def get_conversation(conv_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["messages"] = json.loads(result.pop("messages_json"))
    return result


def list_conversations(project_id: str, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE project_id = ? ORDER BY updated_at DESC LIMIT ?",
        (project_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_conversation(conv_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()


# ─── Memory ──────────────────────────────────────────────────

def save_memory(project_id: str, key: str, value: str):
    ensure_project(project_id)
    conn = _get_conn()
    now = _now()
    conn.execute(
        """INSERT INTO memory (id, project_id, key, value, created_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(project_id, key)
           DO UPDATE SET value = excluded.value, created_at = excluded.created_at""",
        (str(uuid.uuid4()), project_id, key, value, now),
    )
    conn.commit()


def get_all_memories(project_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, key, value, created_at FROM memory WHERE project_id = ? ORDER BY created_at",
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_memory(project_id: str, key: str):
    conn = _get_conn()
    conn.execute(
        "DELETE FROM memory WHERE project_id = ? AND key = ?",
        (project_id, key),
    )
    conn.commit()
