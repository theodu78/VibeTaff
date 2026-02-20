import os
import json
import uuid

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

load_dotenv()

app = FastAPI(title="Vibetaff Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-vercel-ai-ui-message-stream"],
)


def get_client() -> AsyncOpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is not set")
    return AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def sse_event(data: dict | str) -> str:
    if isinstance(data, dict):
        return f"data: {json.dumps(data)}\n\n"
    return f"data: {data}\n\n"


def ui_messages_to_openai(messages: list[dict]) -> list[dict]:
    """Convert Vercel AI SDK UIMessage format to OpenAI message format."""
    result = []
    for msg in messages:
        role = msg.get("role", "user")
        parts = msg.get("parts", [])
        content = ""
        for part in parts:
            if part.get("type") == "text":
                content += part.get("text", "")
        if content:
            result.append({"role": role, "content": content})
    return result


@app.get("/api/health")
async def health():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    return {
        "status": "ok",
        "deepseek_configured": bool(api_key),
    }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    openai_messages = ui_messages_to_openai(messages)

    if not openai_messages:
        return StreamingResponse(
            iter([sse_event({"type": "error", "errorText": "No messages provided"})]),
            media_type="text/event-stream",
        )

    client = get_client()

    async def generate():
        message_id = f"msg_{uuid.uuid4().hex[:40]}"
        text_id = f"txt_{uuid.uuid4().hex[:40]}"

        yield sse_event({"type": "start", "messageId": message_id})
        yield sse_event({"type": "start-step"})
        yield sse_event({"type": "text-start", "id": text_id})

        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=openai_messages,
                stream=True,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    yield sse_event(
                        {"type": "text-delta", "id": text_id, "delta": delta}
                    )

        except Exception as e:
            yield sse_event({"type": "error", "errorText": str(e)})

        yield sse_event({"type": "text-end", "id": text_id})
        yield sse_event({"type": "finish-step"})
        yield sse_event({"type": "finish"})
        yield sse_event("[DONE]")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=11434)
