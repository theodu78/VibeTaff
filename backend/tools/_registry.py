"""Central tool registry. Tools register themselves via the @tool decorator."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

PROJECTS_ROOT = Path.home() / "VibetaffProjects"


@dataclass
class ToolEntry:
    name: str
    description: str
    category: str
    parameters: dict
    handler: Callable
    requires_env: list[str] = field(default_factory=list)
    requires_docs: bool = False
    requires_approval: bool = False


_tools: dict[str, ToolEntry] = {}


def register_tool(entry: ToolEntry):
    _tools[entry.name] = entry


def get_available_tools(project_id: str = "default") -> list[dict]:
    """Return OpenAI tool definitions for tools whose prerequisites are met."""
    from ingestion.store import list_indexed_files

    has_docs = bool(list_indexed_files(project_id))

    available = []
    for entry in _tools.values():
        if entry.requires_env:
            if not all(os.getenv(k) for k in entry.requires_env):
                continue
        if entry.requires_docs and not has_docs:
            continue
        available.append({
            "type": "function",
            "function": {
                "name": entry.name,
                "description": entry.description,
                "parameters": entry.parameters,
            },
        })
    return available


def execute_tool(tool_name: str, arguments: dict, project_id: str = "default") -> str:
    """Execute a tool by name and return the result string for the LLM."""
    entry = _tools.get(tool_name)
    if not entry:
        return f"Erreur : L'outil '{tool_name}' n'existe pas."

    project_dir = PROJECTS_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    try:
        return entry.handler(arguments, project_id, project_dir)
    except Exception as e:
        return f"Erreur système lors de l'exécution de '{tool_name}' : {str(e)}"


def get_approval_required_tools() -> set[str]:
    """Return the set of tool names that require user approval."""
    return {name for name, entry in _tools.items() if entry.requires_approval}


def get_all_tool_definitions() -> list[dict]:
    """Return all tool definitions regardless of gating."""
    return [
        {
            "type": "function",
            "function": {
                "name": entry.name,
                "description": entry.description,
                "parameters": entry.parameters,
            },
        }
        for entry in _tools.values()
    ]


def list_tool_categories() -> dict[str, list[str]]:
    """Return tools grouped by category."""
    categories: dict[str, list[str]] = {}
    for entry in _tools.values():
        categories.setdefault(entry.category, []).append(entry.name)
    return categories
