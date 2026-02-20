import json
import os
import urllib.request
from typing import AsyncIterator
from providers._base import ChatProvider, CompletionChunk, ToolCallDelta


class OllamaProvider(ChatProvider):
    name = "ollama"
    supports_thinking = False

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/")
        self.default_model = "llama3.3"

    def _api_url(self) -> str:
        return self.base_url.replace("/v1/", "/api/tags")

    def is_configured(self) -> bool:
        try:
            urllib.request.urlopen(self._api_url(), timeout=2)
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            resp = urllib.request.urlopen(self._api_url(), timeout=2)
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def create_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[CompletionChunk]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key="ollama", base_url=self.base_url)

        clean_messages = [
            {k: v for k, v in m.items() if k != "reasoning_content"}
            for m in messages
        ]

        kwargs: dict = {
            "model": model or self.default_model,
            "messages": clean_messages,
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
