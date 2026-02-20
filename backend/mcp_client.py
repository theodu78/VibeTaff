"""
MCP (Model Context Protocol) client for VibeTaff.

Manages connections to external MCP servers and exposes their tools
to the agent. Completely optional — works fine if the 'mcp' package
is not installed.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from tools._registry import PROJECTS_ROOT

logger = logging.getLogger(__name__)

MCP_CONFIG_PATH = PROJECTS_ROOT / ".mcp-config.json"
MCP_TOOL_PREFIX = "mcp_"


@dataclass
class MCPServerConfig:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class MCPServerState:
    name: str
    config: MCPServerConfig
    session: object | None = None
    tools: list[dict] = field(default_factory=list)
    connected: bool = False
    error: str | None = None


_servers: dict[str, MCPServerState] = {}
_contexts: dict[str, tuple] = {}


def load_mcp_config() -> dict[str, MCPServerConfig]:
    """Load MCP server configurations from the config file."""
    if not MCP_CONFIG_PATH.exists():
        return {}

    try:
        data = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
        servers = {}
        for name, config in data.get("servers", {}).items():
            servers[name] = MCPServerConfig(
                command=config.get("command", ""),
                args=config.get("args", []),
                env=config.get("env", {}),
            )
        return servers
    except Exception as e:
        logger.error(f"Erreur lecture config MCP : {e}")
        return {}


def _mcp_tool_to_openai(server_name: str, tool) -> dict:
    """Convert an MCP tool to OpenAI tool calling format with a prefixed name."""
    input_schema = (
        tool.inputSchema
        if hasattr(tool, "inputSchema") and tool.inputSchema
        else {"type": "object", "properties": {}}
    )
    return {
        "type": "function",
        "function": {
            "name": f"{MCP_TOOL_PREFIX}{server_name}__{tool.name}",
            "description": f"[{server_name}] {tool.description or tool.name}",
            "parameters": input_schema,
        },
    }


async def connect_server(name: str, config: MCPServerConfig) -> MCPServerState:
    """Connect to a single MCP server via stdio."""
    state = MCPServerState(name=name, config=config)

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        env = {**os.environ, **config.env}

        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=env,
        )

        ctx = stdio_client(params)
        read, write = await ctx.__aenter__()

        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()

        tools_result = await session.list_tools()
        state.tools = [_mcp_tool_to_openai(name, t) for t in tools_result.tools]
        state.session = session
        state.connected = True

        _contexts[name] = (ctx, session)
        logger.info(f"MCP '{name}' connecté — {len(state.tools)} outil(s)")

    except ImportError:
        state.error = "Package 'mcp' non installé. Installer via : pip install mcp"
        logger.warning(state.error)
    except FileNotFoundError:
        state.error = f"Commande introuvable : '{config.command}'. Vérifier que le serveur MCP est installé."
        logger.warning(f"MCP '{name}' : {state.error}")
    except Exception as e:
        state.error = str(e)
        logger.error(f"MCP '{name}' erreur connexion : {e}")

    _servers[name] = state
    return state


async def disconnect_server(name: str):
    """Disconnect from an MCP server."""
    ctx_pair = _contexts.pop(name, None)
    if ctx_pair:
        ctx, session = ctx_pair
        try:
            await session.__aexit__(None, None, None)
            await ctx.__aexit__(None, None, None)
        except Exception:
            pass

    if name in _servers:
        _servers[name].connected = False
        _servers[name].session = None


async def initialize_all():
    """Connect to all configured MCP servers."""
    configs = load_mcp_config()
    if not configs:
        logger.info("Aucun serveur MCP configuré.")
        return

    for name, config in configs.items():
        await connect_server(name, config)


async def shutdown_all():
    """Disconnect all MCP servers."""
    for name in list(_servers.keys()):
        await disconnect_server(name)


def get_mcp_tools() -> list[dict]:
    """Get all available MCP tools in OpenAI format."""
    tools = []
    for state in _servers.values():
        if state.connected:
            tools.extend(state.tools)
    return tools


def is_mcp_tool(tool_name: str) -> bool:
    """Check if a tool name belongs to an MCP server."""
    return tool_name.startswith(MCP_TOOL_PREFIX)


def _find_server_for_tool(tool_name: str) -> tuple[str, str, MCPServerState] | None:
    """Find which MCP server owns a tool. Returns (server_name, original_name, state)."""
    if not is_mcp_tool(tool_name):
        return None

    for state in _servers.values():
        prefix = f"{MCP_TOOL_PREFIX}{state.name}__"
        if tool_name.startswith(prefix):
            original_name = tool_name[len(prefix):]
            return (state.name, original_name, state)
    return None


async def execute_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Execute an MCP tool and return the result as a string for the LLM."""
    match = _find_server_for_tool(tool_name)
    if not match:
        return f"Erreur : L'outil MCP '{tool_name}' n'existe pas."

    server_name, original_name, state = match

    if not state.connected or not state.session:
        return f"Erreur : Le serveur MCP '{server_name}' n'est pas connecté."

    try:
        result = await state.session.call_tool(original_name, arguments)

        texts = []
        for item in result.content:
            if hasattr(item, "text"):
                texts.append(item.text)
            elif hasattr(item, "data"):
                texts.append(str(item.data))

        return "\n".join(texts) if texts else "(aucun résultat)"

    except Exception as e:
        return f"Erreur MCP ({server_name}/{original_name}) : {str(e)}"


def get_servers_status() -> list[dict]:
    """Get status of all configured MCP servers."""
    configs = load_mcp_config()
    result = []
    for name, config in configs.items():
        state = _servers.get(name)
        result.append({
            "name": name,
            "command": config.command,
            "args": config.args,
            "connected": state.connected if state else False,
            "tools_count": len(state.tools) if state else 0,
            "tools": [
                t["function"]["name"].replace(f"{MCP_TOOL_PREFIX}{name}__", "")
                for t in (state.tools if state else [])
            ],
            "error": state.error if state else None,
        })
    return result


def save_mcp_config(servers: dict[str, dict]):
    """Save MCP server configurations."""
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    MCP_CONFIG_PATH.write_text(
        json.dumps({"servers": servers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
