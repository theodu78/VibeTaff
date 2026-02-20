"""
Multi-LLM provider system.

Provides a unified interface to multiple LLM backends (DeepSeek, OpenAI, Anthropic, Ollama).
The agent loop sees only normalized CompletionChunks, never raw provider data.
"""

import json
import logging
import os
from pathlib import Path

from providers._base import ChatProvider, CompletionChunk, ToolCallDelta
from providers.deepseek import DeepSeekProvider
from providers.openai_compat import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)

PROJECTS_ROOT = Path.home() / "VibetaffProjects"

_PROVIDERS: dict[str, ChatProvider] = {
    "deepseek": DeepSeekProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "ollama": OllamaProvider(),
}

FALLBACK_CHAIN = ["deepseek", "openai", "anthropic", "ollama"]


def get_provider(name: str) -> ChatProvider | None:
    return _PROVIDERS.get(name)


def list_providers() -> list[dict]:
    result = []
    for name, provider in _PROVIDERS.items():
        configured = False
        try:
            configured = provider.is_configured()
        except Exception:
            pass
        models = []
        try:
            models = provider.list_models()
        except Exception:
            pass
        result.append({
            "id": name,
            "name": provider.name,
            "models": models,
            "configured": configured,
            "supports_thinking": provider.supports_thinking,
        })
    return result


def get_project_model_config(project_id: str) -> tuple[str, str]:
    """Read the provider/model config for a project, or return defaults."""
    config_file = PROJECTS_ROOT / project_id / "_config" / "model.json"
    if config_file.exists():
        try:
            data = json.loads(config_file.read_text())
            return data.get("provider", "deepseek"), data.get("model", "deepseek-chat")
        except Exception:
            pass
    return "deepseek", "deepseek-chat"


def save_project_model_config(project_id: str, provider: str, model: str):
    """Save the provider/model choice for a project."""
    config_dir = PROJECTS_ROOT / project_id / "_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "model.json"
    config_file.write_text(
        json.dumps({"provider": provider, "model": model}, indent=2),
        encoding="utf-8",
    )


def get_provider_for_project(project_id: str) -> tuple[ChatProvider, str]:
    """Get the configured provider for a project, with automatic fallback."""
    provider_id, model = get_project_model_config(project_id)

    provider = get_provider(provider_id)
    if provider:
        try:
            if provider.is_configured():
                return provider, model
        except Exception:
            pass

    for pid in FALLBACK_CHAIN:
        p = get_provider(pid)
        if p:
            try:
                if p.is_configured():
                    logger.warning(f"Provider '{provider_id}' indisponible, fallback sur '{pid}'")
                    models = p.list_models()
                    return p, models[0] if models else ""
            except Exception:
                continue

    raise RuntimeError("Aucun provider LLM configuré. Ajouter au moins DEEPSEEK_API_KEY dans .env")
