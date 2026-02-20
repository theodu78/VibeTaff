"""
Auto-discovering pluggable tool registry.

Each tool is a separate Python file with a @tool decorator.
Tools are discovered automatically at import time.
"""

import importlib
import pkgutil

from tools._registry import (
    get_available_tools,
    execute_tool,
    get_approval_required_tools,
    get_all_tool_definitions,
    list_tool_categories,
    PROJECTS_ROOT,
)
from tools._base import get_project_instructions

# Auto-discover all tool modules to trigger @tool decorator registration
for _loader, _module_name, _ispkg in pkgutil.walk_packages(
    __path__, prefix=__name__ + "."
):
    _leaf = _module_name.split(".")[-1]
    if _leaf.startswith("_"):
        continue
    importlib.import_module(_module_name)

# Legacy alias for backwards compatibility
TOOL_DEFINITIONS = get_all_tool_definitions()
