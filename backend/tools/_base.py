"""Shared utilities and the @tool decorator."""

from pathlib import Path
from tools._registry import ToolEntry, register_tool, PROJECTS_ROOT


def tool(
    name: str,
    description: str,
    category: str,
    parameters: dict,
    requires_env: list[str] | None = None,
    requires_docs: bool = False,
    requires_approval: bool = False,
):
    """Decorator to register a function as an agent tool."""
    def decorator(func):
        entry = ToolEntry(
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            handler=func,
            requires_env=requires_env or [],
            requires_docs=requires_docs,
            requires_approval=requires_approval,
        )
        register_tool(entry)
        return func
    return decorator


def resolve_safe_path(project_dir: Path, relative_path: str) -> Path | None:
    """Resolve a path and verify it stays inside the project jail."""
    try:
        target = (project_dir / relative_path).resolve()
        project_resolved = project_dir.resolve()
        if not str(target).startswith(str(project_resolved)):
            return None
        return target
    except (ValueError, OSError):
        return None


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} o"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} Ko"
    return f"{size_bytes // (1024 * 1024)} Mo"


HIDDEN_NAMES = {"_config", "_uploads", "MEMORY.md", "todos.json", "contacts.json", "__pycache__", "reunions"}


def list_dir(directory: Path, max_depth: int = 3, _depth: int = 0) -> str:
    """List directory contents recursively as a tree."""
    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        return "(accès refusé)"
    if not entries:
        return "(dossier vide)"

    indent = "  " * _depth
    lines = []
    for entry in entries:
        if entry.name.startswith(".") or (_depth == 0 and entry.name in HIDDEN_NAMES):
            continue
        if entry.is_dir():
            lines.append(f"{indent}📁 {entry.name}/")
            if _depth < max_depth:
                subtree = list_dir(entry, max_depth, _depth + 1)
                if subtree and subtree != "(dossier vide)":
                    lines.append(subtree)
        else:
            size = _format_size(entry.stat().st_size)
            lines.append(f"{indent}📄 {entry.name} ({size})")
    return "\n".join(lines) if lines else "(dossier vide)"


def get_project_instructions(project_id: str) -> str | None:
    """Read project-specific instructions if they exist."""
    instructions_file = PROJECTS_ROOT / project_id / "_config" / "instructions.md"
    if instructions_file.exists():
        try:
            return instructions_file.read_text(encoding="utf-8").strip()
        except Exception:
            return None
    return None
