"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class ToolCallDelta:
    index: int
    id: str | None = None
    name: str | None = None
    arguments_delta: str | None = None


@dataclass
class UsageData:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class CompletionChunk:
    """Normalized chunk — the agent loop only sees this, never raw provider data."""
    text_delta: str | None = None
    reasoning_delta: str | None = None
    tool_calls: list[ToolCallDelta] | None = None
    finish_reason: str | None = None
    usage: UsageData | None = None


class ChatProvider(ABC):
    name: str
    supports_thinking: bool = False
    supports_tool_calling: bool = True

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def create_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        ...
        yield  # make it a generator  # pragma: no cover

    @abstractmethod
    def list_models(self) -> list[str]:
        ...
