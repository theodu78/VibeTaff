import json
import os
from typing import AsyncIterator
from providers._base import ChatProvider, CompletionChunk, ToolCallDelta


class AnthropicProvider(ChatProvider):
    name = "anthropic"
    supports_thinking = True
    supports_tool_calling = True

    def __init__(self):
        self.default_model = "claude-sonnet-4-20250514"

    def is_configured(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def list_models(self) -> list[str]:
        return ["claude-sonnet-4-20250514", "claude-haiku-3.5"]

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """Convert OpenAI message format to Anthropic Messages format."""
        system = ""
        converted = []

        for msg in messages:
            role = msg.get("role", "user")

            if role == "system":
                system = msg.get("content", "")
                continue

            if role == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": msg.get("content", ""),
                    }],
                })
                continue

            if role == "assistant" and "tool_calls" in msg:
                content = []
                text = msg.get("content")
                if text:
                    content.append({"type": "text", "text": text})
                for tc in msg.get("tool_calls", []):
                    try:
                        input_data = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        input_data = {}
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": input_data,
                    })
                converted.append({"role": "assistant", "content": content})
                continue

            converted.append({
                "role": role,
                "content": msg.get("content", ""),
            })

        return system, converted

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert OpenAI tool format to Anthropic tool format."""
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"].get("parameters", {"type": "object", "properties": {}}),
            }
            for t in tools
        ]

    async def create_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        system, converted_messages = self._convert_messages(messages)

        kwargs: dict = {
            "model": model or self.default_model,
            "messages": converted_messages,
            "max_tokens": 8192,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        current_tool_index = -1

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if hasattr(block, "type") and block.type == "tool_use":
                        current_tool_index += 1
                        yield CompletionChunk(tool_calls=[ToolCallDelta(
                            index=current_tool_index,
                            id=block.id,
                            name=block.name,
                        )])

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if hasattr(delta, "type"):
                        if delta.type == "text_delta":
                            yield CompletionChunk(text_delta=delta.text)
                        elif delta.type == "thinking_delta":
                            yield CompletionChunk(reasoning_delta=delta.thinking)
                        elif delta.type == "input_json_delta":
                            yield CompletionChunk(tool_calls=[ToolCallDelta(
                                index=current_tool_index,
                                arguments_delta=delta.partial_json,
                            )])

                elif event.type == "message_delta":
                    stop = getattr(event.delta, "stop_reason", None)
                    if stop == "tool_use":
                        yield CompletionChunk(finish_reason="tool_calls")
                    elif stop == "end_turn":
                        yield CompletionChunk(finish_reason="stop")
