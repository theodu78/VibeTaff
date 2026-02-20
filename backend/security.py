"""
Security module: rate limiting, input validation, and audit logging.
"""

import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from collections import deque

PROJECTS_ROOT = Path.home() / "VibetaffProjects"
AUDIT_LOG_PATH = PROJECTS_ROOT / ".audit.log"

# ─── Rate Limiter ────────────────────────────────────────────

MAX_LLM_CALLS_PER_MINUTE = 20
MAX_LLM_CALLS_PER_HOUR = 200

_call_timestamps: deque[float] = deque()


def check_rate_limit() -> str | None:
    """
    Returns an error message if rate limited, None if OK.
    """
    now = time.time()

    while _call_timestamps and _call_timestamps[0] < now - 3600:
        _call_timestamps.popleft()

    recent_minute = sum(1 for t in _call_timestamps if t > now - 60)
    if recent_minute >= MAX_LLM_CALLS_PER_MINUTE:
        return (
            f"Limite de {MAX_LLM_CALLS_PER_MINUTE} appels/minute atteinte. "
            "Patientez quelques secondes."
        )

    total_hour = len(_call_timestamps)
    if total_hour >= MAX_LLM_CALLS_PER_HOUR:
        return (
            f"Limite de {MAX_LLM_CALLS_PER_HOUR} appels/heure atteinte. "
            "Patientez avant de réessayer."
        )

    _call_timestamps.append(now)
    return None


# ─── Input Validation ────────────────────────────────────────

MAX_MESSAGE_LENGTH = 50_000
MAX_MESSAGES_PER_REQUEST = 100
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 Mo
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".eml", ".msg"}


def validate_chat_input(body: dict) -> str | None:
    """Validate chat request body. Returns error message or None."""
    messages = body.get("messages", [])

    if not messages:
        return "Aucun message fourni."

    if len(messages) > MAX_MESSAGES_PER_REQUEST:
        return f"Trop de messages ({len(messages)}). Maximum : {MAX_MESSAGES_PER_REQUEST}."

    for msg in messages:
        parts = msg.get("parts", [])
        for part in parts:
            if part.get("type") == "text":
                text = part.get("text", "")
                if len(text) > MAX_MESSAGE_LENGTH:
                    return (
                        f"Message trop long ({len(text)} caractères). "
                        f"Maximum : {MAX_MESSAGE_LENGTH}."
                    )

    return None


def validate_file_upload(filename: str, size_bytes: int) -> str | None:
    """Validate an uploaded file. Returns error message or None."""
    if not filename:
        return "Aucun nom de fichier."

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return (
            f"Type '{ext}' non supporté. "
            f"Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        size_mb = size_bytes // (1024 * 1024)
        return f"Fichier trop volumineux ({size_mb} Mo). Maximum : 100 Mo."

    return None


# ─── Audit Logging ───────────────────────────────────────────

_audit_logger = logging.getLogger("vibetaff.audit")


def _ensure_audit_log():
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    if not _audit_logger.handlers:
        handler = logging.FileHandler(str(AUDIT_LOG_PATH), encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        _audit_logger.addHandler(handler)
        _audit_logger.setLevel(logging.INFO)


def audit_log(event_type: str, details: dict):
    """Log a security-relevant event to the audit file."""
    _ensure_audit_log()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **details,
    }
    _audit_logger.info(json.dumps(entry, ensure_ascii=False))


def log_tool_execution(tool_name: str, arguments: dict, result_preview: str):
    audit_log("tool_execution", {
        "tool": tool_name,
        "args_keys": list(arguments.keys()),
        "result_length": len(result_preview),
        "result_preview": result_preview[:200],
    })


def log_llm_call(model: str, message_count: int):
    audit_log("llm_call", {
        "model": model,
        "message_count": message_count,
    })


def log_file_ingestion(filename: str, status: str, chunks: int = 0):
    audit_log("file_ingestion", {
        "filename": filename,
        "status": status,
        "chunks": chunks,
    })


def log_security_event(event: str, details: str):
    audit_log("security", {
        "event": event,
        "details": details,
    })
