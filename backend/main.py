import os
import json
import uuid

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from tools import TOOL_DEFINITIONS, execute_tool

load_dotenv()

MAX_AGENT_STEPS = 5
SYSTEM_PROMPT = """Tu es Vibetaff, un assistant IA spécialisé dans l'analyse de documents professionnels (contrats, bilans financiers, factures, e-mails).

Tu as accès à des outils pour manipuler les fichiers du projet de l'utilisateur. Utilise-les quand c'est pertinent.

Règles :
- Réponds toujours en français.
- Sois concis et structuré.
- Quand tu utilises un outil, explique brièvement pourquoi.
- Si un outil renvoie une erreur, lis le message d'erreur et corrige ton appel (ne réessaie pas la même chose)."""

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
    result = [{"role": "system", "content": SYSTEM_PROMPT}]
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
    return {"status": "ok", "deepseek_configured": bool(api_key)}


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    openai_messages = ui_messages_to_openai(messages)

    if len(openai_messages) <= 1:
        return StreamingResponse(
            iter([sse_event({"type": "error", "errorText": "No messages provided"})]),
            media_type="text/event-stream",
        )

    client = get_client()

    async def generate():
        message_id = f"msg_{uuid.uuid4().hex[:40]}"
        yield sse_event({"type": "start", "messageId": message_id})

        nonlocal openai_messages
        steps = 0

        while steps < MAX_AGENT_STEPS:
            steps += 1
            yield sse_event({"type": "start-step"})

            try:
                response = await client.chat.completions.create(
                    model="deepseek-chat",
                    messages=openai_messages,
                    tools=TOOL_DEFINITIONS,
                    stream=True,
                )
            except Exception as e:
                yield sse_event({"type": "error", "errorText": str(e)})
                break

            text_content = ""
            tool_calls_accum: dict[int, dict] = {}
            finish_reason = None

            async for chunk in response:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue

                if choice.finish_reason:
                    finish_reason = choice.finish_reason

                delta = choice.delta

                # Stream text content
                if delta.content:
                    if not text_content:
                        text_id = f"txt_{uuid.uuid4().hex[:40]}"
                        yield sse_event({"type": "text-start", "id": text_id})
                    text_content += delta.content
                    yield sse_event(
                        {"type": "text-delta", "id": text_id, "delta": delta.content}
                    )

                # Accumulate tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accum:
                            tool_calls_accum[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_accum[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_accum[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_accum[idx]["arguments"] += (
                                tc.function.arguments
                            )

            # Close text block if we streamed any text
            if text_content:
                yield sse_event({"type": "text-end", "id": text_id})

            # If we got tool calls, execute them and loop
            if finish_reason == "tool_calls" and tool_calls_accum:
                assistant_msg = {"role": "assistant", "content": None, "tool_calls": []}

                for idx in sorted(tool_calls_accum.keys()):
                    tc = tool_calls_accum[idx]
                    assistant_msg["tool_calls"].append(
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                    )

                openai_messages.append(assistant_msg)

                for idx in sorted(tool_calls_accum.keys()):
                    tc = tool_calls_accum[idx]
                    tool_call_id = tc["id"]
                    tool_name = tc["name"]

                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    # SSE: tool input available
                    yield sse_event(
                        {
                            "type": "tool-input-start",
                            "toolCallId": tool_call_id,
                            "toolName": tool_name,
                        }
                    )
                    yield sse_event(
                        {
                            "type": "tool-input-available",
                            "toolCallId": tool_call_id,
                            "toolName": tool_name,
                            "input": args,
                        }
                    )

                    # Execute the tool
                    result = execute_tool(tool_name, args)

                    # SSE: tool output
                    yield sse_event(
                        {
                            "type": "tool-output-available",
                            "toolCallId": tool_call_id,
                            "output": result,
                        }
                    )

                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result,
                        }
                    )

                yield sse_event({"type": "finish-step"})
                # Loop back to call DeepSeek with tool results
                continue

            # No tool calls — we're done
            yield sse_event({"type": "finish-step"})
            break

        # Circuit breaker message
        if steps >= MAX_AGENT_STEPS:
            breaker_id = f"txt_{uuid.uuid4().hex[:40]}"
            yield sse_event({"type": "start-step"})
            yield sse_event({"type": "text-start", "id": breaker_id})
            yield sse_event(
                {
                    "type": "text-delta",
                    "id": breaker_id,
                    "delta": "\n\n⚠️ J'ai atteint la limite d'actions par message. Reformule ta demande si besoin.",
                }
            )
            yield sse_event({"type": "text-end", "id": breaker_id})
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
