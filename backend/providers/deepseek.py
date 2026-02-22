import os
from typing import AsyncIterator
from providers._base import ChatProvider, CompletionChunk, ToolCallDelta, UsageData


class DeepSeekProvider(ChatProvider):
    name = "deepseek"
    supports_thinking = True

    def __init__(self):
        self.default_model = "deepseek-chat"
        self.base_url = "https://api.deepseek.com"

    def is_configured(self) -> bool:
        return bool(os.getenv("DEEPSEEK_API_KEY"))

    def list_models(self) -> list[str]:
        return ["deepseek-chat", "deepseek-reasoner"]

    async def create_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=self.base_url,
        )

        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "stream": True,
            "max_tokens": 8192,
            "extra_body": {"thinking": {"type": "enabled"}},
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)

        async for chunk in response:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                if hasattr(chunk, "usage") and chunk.usage:
                    yield CompletionChunk(
                        usage=UsageData(
                            prompt_tokens=getattr(chunk.usage, "prompt_tokens", 0) or 0,
                            completion_tokens=getattr(chunk.usage, "completion_tokens", 0) or 0,
                        )
                    )
                continue

            delta = choice.delta
            result = CompletionChunk(finish_reason=choice.finish_reason)

            rc = getattr(delta, "reasoning_content", None)
            if rc:
                result.reasoning_delta = rc

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
