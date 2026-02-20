import os
from typing import AsyncIterator
from providers._base import ChatProvider, CompletionChunk, ToolCallDelta


def _strip_reasoning(messages: list[dict]) -> list[dict]:
    """Remove reasoning_content field that non-DeepSeek providers don't understand."""
    return [{k: v for k, v in m.items() if k != "reasoning_content"} for m in messages]


class OpenAIProvider(ChatProvider):
    name = "openai"
    supports_thinking = False

    def __init__(self):
        self.default_model = "gpt-4o"

    def is_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def list_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"]

    async def create_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        kwargs: dict = {
            "model": model or self.default_model,
            "messages": _strip_reasoning(messages),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)

        async for chunk in response:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta
            result = CompletionChunk(finish_reason=choice.finish_reason)

            if delta.content:
                result.text_delta = delta.content

            if delta.tool_calls:
                result.tool_calls = []
                for tc in delta.tool_calls:
                    result.tool_calls.append(ToolCallDelta(
                        index=tc.index,
                        id=tc.id or None,
                        name=tc.function.name if tc.function and tc.function.name else None,
                        arguments_delta=tc.function.arguments if tc.function and tc.function.arguments else None,
                    ))

            yield result
