import os
import json
import time
import uuid
import asyncio
import locale
import shutil
import logging
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from tools import get_available_tools, execute_tool, get_approval_required_tools, PROJECTS_ROOT, get_project_instructions
from providers import get_provider_for_project, list_providers, save_project_model_config
from mcp_client import (
    initialize_all as mcp_init,
    shutdown_all as mcp_shutdown,
    get_mcp_tools,
    is_mcp_tool,
    execute_mcp_tool,
    get_servers_status as mcp_servers_status,
    load_mcp_config,
    save_mcp_config,
    connect_server,
    disconnect_server,
    MCPServerConfig,
)
from ingestion.pipeline import ingest_file
from ingestion.store import list_indexed_files, delete_file_chunks
from ingestion.extractor import SUPPORTED_EXTENSIONS
from database import (
    create_conversation,
    save_conversation,
    get_conversation,
    list_conversations,
    delete_conversation,
    get_all_memories,
    ensure_project,
)
from security import (
    check_rate_limit,
    validate_chat_input,
    validate_file_upload,
    log_tool_execution,
    log_llm_call,
    log_file_ingestion,
    log_security_event,
)
from task_queue import task_queue, Task, TaskStatus
from heartbeat import Heartbeat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

MAX_AGENT_STEPS = 10
APPROVAL_REQUIRED_TOOLS = get_approval_required_tools()
APPROVAL_TIMEOUT = 120

_pending_approvals: dict[str, asyncio.Event] = {}
_approval_results: dict[str, bool] = {}
_recent_uploads: dict[str, list[tuple[str, float]]] = {}

UPLOAD_CONTEXT_MAX_AGE = 120  # 2 minutes


def _track_upload(project_id: str, filename: str):
    _recent_uploads.setdefault(project_id, []).append((filename, time.time()))


def _consume_recent_uploads(project_id: str) -> list[str]:
    """Return and clear recent uploads for a project (within max age)."""
    now = time.time()
    entries = _recent_uploads.get(project_id, [])
    recent = [name for name, ts in entries if now - ts < UPLOAD_CONTEXT_MAX_AGE]
    _recent_uploads[project_id] = []
    return recent
BASE_SYSTEM_PROMPT = """Tu es Vibetaff, un assistant IA spécialisé dans l'analyse de documents professionnels (contrats, bilans financiers, factures, e-mails).

Tu as accès à des outils pour manipuler les fichiers du projet de l'utilisateur. Utilise-les quand c'est pertinent.

Règles :
- Réponds toujours en français.
- Sois concis et structuré.
- Quand tu utilises un outil, explique brièvement pourquoi.
- Si un outil renvoie une erreur, lis le message d'erreur et corrige ton appel (ne réessaie pas la même chose).
- Si l'utilisateur exprime une préférence durable (format, unité, habitude), utilise save_to_long_term_memory pour la mémoriser.

Règle FONDAMENTALE sur les documents :
- Quand l'utilisateur pose une question sur le contenu de ses documents (devis, contrat, rapport, facture, etc.), utilise TOUJOURS query_project_memory EN PREMIER. C'est une recherche sémantique dans la base de données vectorielle, elle trouve les passages pertinents instantanément.
- Ne fais PAS list_project_files puis read_file_content pour chercher une info. C'est lent et tu gaspilles tes étapes.
- Utilise read_file_content UNIQUEMENT si query_project_memory n'a pas trouvé de résultat, ou si l'utilisateur demande explicitement de lire un fichier précis.
- query_project_memory cherche dans TOUS les documents indexés à la fois. C'est ta mémoire principale.
- Quand l'utilisateur te demande de noter une tâche, un rappel ou un "à faire", utilise manage_todo avec l'action 'add'.
- Quand l'utilisateur te demande de faire un compte-rendu de réunion, utilise save_meeting_note pour créer un fichier structuré dans le dossier reunions/.
- Quand tu utilises manage_todo avec l'action 'list', un bloc visuel interactif est automatiquement affiché à l'utilisateur. Ne reproduis PAS la liste en texte, tableau ou récapitulatif. Dis simplement une phrase courte comme "Voici vos tâches." ou réponds directement à la question de l'utilisateur.
- Après manage_todo avec 'add', 'update' ou 'delete', confirme brièvement l'action en une phrase. Le bloc visuel se met à jour tout seul.
- Quand l'utilisateur donne des coordonnées (nom, téléphone, email, adresse), utilise manage_contacts avec l'action 'add'. Ne crée PAS de fichier .md ou .json manuellement pour les contacts.
- Quand l'utilisateur demande "envoie un mail à X", utilise manage_contacts avec l'action 'search' pour trouver l'email du contact, puis utilise draft_email pour rédiger le brouillon.
- Quand tu utilises manage_contacts avec 'list', un bloc visuel est affiché. Ne reproduis PAS la liste en texte.
- Pour TOUT email, utilise TOUJOURS l'outil draft_email. Ne rédige JAMAIS un email en texte brut dans ta réponse. L'outil draft_email affiche un composant visuel avec un bouton pour ouvrir le client mail. Ne dis JAMAIS "je ne peux pas envoyer d'email" — draft_email génère un lien mailto qui ouvre le client mail de l'utilisateur.

Règles CRITIQUES sur les outils :
- Ne fais JAMAIS plus de 2 appels à web_search pour la même question.
- Ne fais JAMAIS plus de 3 appels à read_file_content par question.
- Privilégie TOUJOURS donner une réponse (même partielle) plutôt que de boucler sur des appels d'outils.
- Si un outil ne donne pas le résultat attendu, n'essaie PAS 5 variantes. Donne ta meilleure réponse avec les infos disponibles.
- Économise tes étapes : tu as un maximum de 10 actions par message, ne les gaspille pas.

Règles de CONCISION et EFFICACITÉ :
- Sois DÉCISIF. Ne tourne pas en rond. Si tu hésites entre 2 options, choisis la plus simple et agis.
- Pour une action simple (déplacer un fichier, créer une note, ajouter une tâche) : 1 à 2 appels d'outils maximum. Ne fais pas list + read + query + list_memories avant d'agir.
- Si l'utilisateur dit "mets ce fichier là-bas", fais-le directement. Ne lis pas le fichier, ne cherche pas dans la mémoire, ne liste pas 3 fois les dossiers.
- Si tu ne comprends pas la demande, DEMANDE à l'utilisateur au lieu de deviner en faisant 5 appels d'outils.
- Tes réponses texte doivent être COURTES : 1-3 phrases maximum pour une action simple. Pas de récapitulatif, pas de "Action effectuée :", pas de liste à puces inutile.
- Ne répète JAMAIS ce que l'utilisateur vient de dire. Il le sait déjà.

Fichiers joints :
- Quand le message commence par [Fichier(s) joint(s) : ...], le fichier vient d'être uploadé.
- Utilise DIRECTEMENT read_file_content avec le chemin "_uploads/<nom_du_fichier>" pour lire son contenu. Ne fais PAS list_project_files d'abord.
- Si le fichier a été indexé, tu peux aussi utiliser query_project_memory pour des questions précises sur son contenu."""


def build_system_prompt(project_id: str) -> str:
    from datetime import datetime

    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    except locale.Error:
        pass
    today = datetime.now().strftime("%A %d %B %Y")
    prompt = BASE_SYSTEM_PROMPT + f"\n\nDate du jour : {today}."

    instructions = get_project_instructions(project_id)
    if instructions:
        prompt += "\n\nInstructions spécifiques à ce projet :\n" + instructions

    memories = get_all_memories(project_id)
    if memories:
        memory_block = "\n".join(f"- {m['key']} : {m['value']}" for m in memories)
        prompt += "\n\nMémoire à long terme (préférences et infos de l'utilisateur) :\n" + memory_block

    return prompt

DAEMON_DIR = Path.home() / ".vibetaff"
PID_FILE = DAEMON_DIR / "daemon.pid"

heartbeat = Heartbeat(task_queue)


def _write_pid():
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _remove_pid():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    _write_pid()
    try:
        await mcp_init()
    except Exception as e:
        logger.warning(f"MCP init ignoré : {e}")
    await task_queue.start()
    await heartbeat.start()
    logger.info(f"Daemon ready (PID {os.getpid()})")
    yield
    await heartbeat.stop()
    await task_queue.stop()
    try:
        await mcp_shutdown()
    except Exception:
        pass
    _remove_pid()


app = FastAPI(title="Vibetaff Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-vercel-ai-ui-message-stream"],
)


def sse_event(data: dict | str) -> str:
    if isinstance(data, dict):
        return f"data: {json.dumps(data)}\n\n"
    return f"data: {data}\n\n"


def ui_messages_to_openai(messages: list[dict], project_id: str = "default") -> list[dict]:
    """Convert Vercel AI SDK UIMessage format to OpenAI message format."""
    system_prompt = build_system_prompt(project_id)
    result = [{"role": "system", "content": system_prompt}]
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

    validation_error = validate_chat_input(body)
    if validation_error:
        log_security_event("chat_validation_failed", validation_error)
        return StreamingResponse(
            iter([sse_event({"type": "error", "errorText": validation_error})]),
            media_type="text/event-stream",
        )

    rate_error = check_rate_limit()
    if rate_error:
        log_security_event("rate_limited", rate_error)
        return StreamingResponse(
            iter([sse_event({"type": "error", "errorText": rate_error})]),
            media_type="text/event-stream",
        )

    messages = body.get("messages", [])
    project_id = body.get("project_id", "default")
    conversation_id = body.get("conversation_id")
    openai_messages = ui_messages_to_openai(messages, project_id)

    recent_files = _consume_recent_uploads(project_id)
    if recent_files:
        last_user_msg = None
        for i in range(len(openai_messages) - 1, -1, -1):
            if openai_messages[i].get("role") == "user":
                last_user_msg = openai_messages[i]
                break
        if last_user_msg:
            already_tagged = "[Fichier(s) joint(s)" in last_user_msg.get("content", "")
            if not already_tagged:
                files_str = ", ".join(f'"{f}"' for f in recent_files)
                last_user_msg["content"] = (
                    f"[Fichier(s) joint(s) : {files_str}]\n\n"
                    + last_user_msg["content"]
                )

    if conversation_id:
        save_conversation(conversation_id, messages)

    if len(openai_messages) <= 1:
        return StreamingResponse(
            iter([sse_event({"type": "error", "errorText": "No messages provided"})]),
            media_type="text/event-stream",
        )

    try:
        provider, model_name = get_provider_for_project(project_id)
    except RuntimeError as e:
        return StreamingResponse(
            iter([sse_event({"type": "error", "errorText": str(e)})]),
            media_type="text/event-stream",
        )

    async def generate():
        message_id = f"msg_{uuid.uuid4().hex[:40]}"
        yield sse_event({"type": "start", "messageId": message_id})

        nonlocal openai_messages
        steps = 0
        tool_call_history: list[tuple[str, str]] = []
        available_tools = get_available_tools(project_id) + get_mcp_tools()

        while steps < MAX_AGENT_STEPS:
            steps += 1
            yield sse_event({"type": "start-step"})

            yield sse_event({
                "type": "data-progress",
                "id": "agent-progress",
                "data": {"step": steps, "maxSteps": MAX_AGENT_STEPS, "label": f"Réflexion en cours ({provider.name})..."},
            })

            log_llm_call(f"{provider.name}/{model_name}", len(openai_messages))

            try:
                stream = provider.create_completion(
                    openai_messages,
                    tools=available_tools if available_tools else None,
                    model=model_name,
                )
            except Exception as e:
                log_security_event("llm_error", str(e))
                yield sse_event({"type": "error", "errorText": str(e)})
                break

            text_content = ""
            reasoning_content = ""
            reasoning_started = False
            tool_calls_accum: dict[int, dict] = {}
            finish_reason = None
            text_id = None
            reasoning_id = None

            try:
                async for chunk in stream:
                    if chunk.finish_reason:
                        finish_reason = chunk.finish_reason

                    if chunk.reasoning_delta:
                        if not reasoning_started:
                            reasoning_id = f"reason_{uuid.uuid4().hex[:20]}"
                            reasoning_started = True
                            yield sse_event({"type": "reasoning-start", "id": reasoning_id})
                        reasoning_content += chunk.reasoning_delta
                        yield sse_event({"type": "reasoning-delta", "id": reasoning_id, "delta": chunk.reasoning_delta})

                    if chunk.text_delta:
                        if reasoning_started and reasoning_id:
                            yield sse_event({"type": "reasoning-end", "id": reasoning_id})
                            reasoning_id = None

                        if not text_content:
                            text_id = f"txt_{uuid.uuid4().hex[:40]}"
                            yield sse_event({"type": "text-start", "id": text_id})
                        text_content += chunk.text_delta
                        yield sse_event({"type": "text-delta", "id": text_id, "delta": chunk.text_delta})

                    if chunk.tool_calls:
                        if reasoning_started and reasoning_id:
                            yield sse_event({"type": "reasoning-end", "id": reasoning_id})
                            reasoning_id = None

                        for tc in chunk.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_accum:
                                tool_calls_accum[idx] = {"id": "", "name": "", "arguments": ""}
                            if tc.id:
                                tool_calls_accum[idx]["id"] = tc.id
                            if tc.name:
                                tool_calls_accum[idx]["name"] = tc.name
                            if tc.arguments_delta:
                                tool_calls_accum[idx]["arguments"] += tc.arguments_delta
            except Exception as e:
                log_security_event("llm_stream_error", str(e))
                yield sse_event({"type": "error", "errorText": str(e)})
                break

            if reasoning_started and reasoning_id:
                yield sse_event({"type": "reasoning-end", "id": reasoning_id})

            if not text_content and not tool_calls_accum and reasoning_content:
                text_id = f"txt_{uuid.uuid4().hex[:40]}"
                yield sse_event({"type": "text-start", "id": text_id})
                yield sse_event({"type": "text-delta", "id": text_id, "delta": reasoning_content})
                text_content = reasoning_content
                yield sse_event({"type": "text-end", "id": text_id})
                logger.warning("LLM produced reasoning but no text — reasoning emitted as text fallback")

            if text_content and text_id:
                yield sse_event({"type": "text-end", "id": text_id})

            if finish_reason == "tool_calls" and tool_calls_accum:
                assistant_msg = {
                    "role": "assistant",
                    "content": text_content or None,
                    "reasoning_content": reasoning_content or None,
                    "tool_calls": [],
                }

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

                    args_sig = json.dumps(args, sort_keys=True)
                    call_sig = (tool_name, args_sig)

                    loop_detected = False
                    if call_sig in tool_call_history:
                        loop_detected = True
                    elif len(tool_call_history) >= 3:
                        recent = tool_call_history[-3:]
                        names = [c[0] for c in recent]
                        if len(names) >= 3 and names[-1] == names[-3] and names[-2] != names[-1]:
                            loop_detected = True

                    tool_call_history.append(call_sig)

                    if loop_detected:
                        result = (
                            f"BOUCLE DÉTECTÉE : Tu as déjà appelé '{tool_name}' avec ces mêmes arguments. "
                            "STOP. Donne ta meilleure réponse avec les informations que tu as déjà collectées. "
                            "Ne rappelle PAS cet outil."
                        )
                        yield sse_event({
                            "type": "tool-input-start",
                            "toolCallId": tool_call_id,
                            "toolName": tool_name,
                        })
                        yield sse_event({
                            "type": "tool-input-available",
                            "toolCallId": tool_call_id,
                            "toolName": tool_name,
                            "input": args,
                        })
                        yield sse_event({
                            "type": "tool-output-available",
                            "toolCallId": tool_call_id,
                            "output": result,
                        })
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result,
                        })
                        log_tool_execution(tool_name, args, result)
                        continue

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

                    yield sse_event({
                        "type": "data-progress",
                        "id": "agent-progress",
                        "data": {
                            "step": steps,
                            "maxSteps": MAX_AGENT_STEPS,
                            "label": f"Exécution : {tool_name}",
                            "toolIndex": idx + 1,
                            "toolTotal": len(tool_calls_accum),
                        },
                    })

                    approved = True
                    if tool_name in APPROVAL_REQUIRED_TOOLS:
                        approval_id = f"approval_{uuid.uuid4().hex[:12]}"
                        event = asyncio.Event()
                        _pending_approvals[approval_id] = event

                        yield sse_event({
                            "type": "data-approval",
                            "id": approval_id,
                            "data": {
                                "approvalId": approval_id,
                                "toolCallId": tool_call_id,
                                "toolName": tool_name,
                                "args": args,
                                "status": "pending",
                            },
                        })

                        try:
                            await asyncio.wait_for(event.wait(), timeout=APPROVAL_TIMEOUT)
                        except asyncio.TimeoutError:
                            _approval_results[approval_id] = False

                        approved = _approval_results.pop(approval_id, False)
                        _pending_approvals.pop(approval_id, None)

                        yield sse_event({
                            "type": "data-approval",
                            "id": approval_id,
                            "data": {
                                "approvalId": approval_id,
                                "toolCallId": tool_call_id,
                                "toolName": tool_name,
                                "args": args,
                                "status": "approved" if approved else "denied",
                            },
                        })

                    if approved:
                        if is_mcp_tool(tool_name):
                            result = await execute_mcp_tool(tool_name, args)
                        else:
                            result = execute_tool(tool_name, args, project_id)
                        log_tool_execution(tool_name, args, result)

                        if tool_name == "manage_todo":
                            todos_data = _read_todos_file(project_id)
                            yield sse_event({
                                "type": "data-todos",
                                "id": "todos_block",
                                "data": {
                                    "projectId": project_id,
                                    "todos": todos_data,
                                },
                            })

                        if tool_name == "manage_contacts":
                            contacts_data = _read_contacts_file(project_id)
                            yield sse_event({
                                "type": "data-contacts",
                                "id": "contacts_block",
                                "data": {
                                    "projectId": project_id,
                                    "contacts": contacts_data,
                                },
                            })
                    else:
                        result = "Action refusée par l'utilisateur."
                        log_tool_execution(tool_name, args, result)

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


@app.post("/api/tool-approval/{approval_id}")
async def tool_approval(approval_id: str, request: Request):
    """Approve or deny a pending tool execution."""
    body = await request.json()
    approved = body.get("approved", False)
    _approval_results[approval_id] = approved
    event = _pending_approvals.get(approval_id)
    if event:
        event.set()
        return {"status": "ok"}
    return {"status": "error", "message": "Approval ID not found or expired"}


def _read_todos_file(project_id: str) -> list[dict]:
    """Read the todos.json file for a project."""
    todos_path = PROJECTS_ROOT / project_id / "todos.json"
    if not todos_path.exists():
        return []
    try:
        return json.loads(todos_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write_todos_file(project_id: str, todos: list[dict]):
    """Write the todos.json file for a project."""
    project_dir = PROJECTS_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    todos_path = project_dir / "todos.json"
    todos_path.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/project/{project_id}/todos")
async def get_todos(project_id: str):
    """Return all todos for a project."""
    todos = _read_todos_file(project_id)
    return {"todos": todos}


@app.put("/api/project/{project_id}/todos/{task_id}")
async def update_todo(project_id: str, task_id: int, request: Request):
    """Update a specific todo item."""
    body = await request.json()
    todos = _read_todos_file(project_id)
    target = next((t for t in todos if t.get("id") == task_id), None)
    if not target:
        return {"status": "error", "message": f"Tâche #{task_id} introuvable."}

    for field in ("statut", "priorite", "deadline", "tache"):
        if field in body:
            target[field] = body[field]

    from datetime import datetime
    target["modifie_le"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _write_todos_file(project_id, todos)
    return {"status": "ok", "todo": target}


@app.delete("/api/project/{project_id}/todos/{task_id}")
async def delete_todo(project_id: str, task_id: int):
    """Delete a specific todo item."""
    todos = _read_todos_file(project_id)
    before = len(todos)
    todos = [t for t in todos if t.get("id") != task_id]
    if len(todos) == before:
        return {"status": "error", "message": f"Tâche #{task_id} introuvable."}
    _write_todos_file(project_id, todos)
    return {"status": "ok"}


def _read_contacts_file(project_id: str) -> list[dict]:
    path = PROJECTS_ROOT / project_id / "contacts.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


@app.get("/api/project/{project_id}/contacts")
async def get_contacts(project_id: str):
    return {"contacts": _read_contacts_file(project_id)}


@app.delete("/api/project/{project_id}/contacts/{contact_id}")
async def delete_contact_api(project_id: str, contact_id: int):
    contacts = _read_contacts_file(project_id)
    before = len(contacts)
    contacts = [c for c in contacts if c.get("id") != contact_id]
    if len(contacts) == before:
        return {"status": "error", "message": f"Contact #{contact_id} introuvable."}
    path = PROJECTS_ROOT / project_id / "contacts.json"
    path.write_text(json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "ok"}


@app.post("/api/project/{project_id}/ingest")
async def ingest(project_id: str, file: UploadFile = File(...)):
    """Upload and ingest a document into the project's vector store."""
    if not file.filename:
        return {"status": "error", "message": "Aucun fichier fourni."}

    content = await file.read()

    file_error = validate_file_upload(file.filename, len(content))
    if file_error:
        log_security_event("file_validation_failed", f"{file.filename}: {file_error}")
        return {"status": "error", "message": file_error}

    project_dir = PROJECTS_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    upload_dir = project_dir / "_uploads"
    upload_dir.mkdir(exist_ok=True)

    dest = upload_dir / file.filename
    try:
        dest.write_bytes(content)
    except Exception as e:
        return {"status": "error", "message": f"Erreur lors de l'upload : {str(e)}"}

    logger.info(f"Fichier '{file.filename}' reçu ({len(content)} octets), lancement du pipeline...")
    result = ingest_file(dest, project_id)

    if result.get("status") == "ok":
        _track_upload(project_id, file.filename)

    log_file_ingestion(
        file.filename,
        result.get("status", "error"),
        result.get("chunks_stored", 0),
    )
    return result


@app.get("/api/project/{project_id}/documents")
async def get_documents(project_id: str):
    """List all indexed documents for a project."""
    files = list_indexed_files(project_id)
    return {"project_id": project_id, "documents": files}


@app.delete("/api/project/{project_id}/documents/{file_name}")
async def delete_document(project_id: str, file_name: str):
    """Remove a document from the index and delete the uploaded file."""
    delete_file_chunks(project_id, file_name)

    upload_path = PROJECTS_ROOT / project_id / "_uploads" / file_name
    if upload_path.exists():
        upload_path.unlink()

    return {"status": "ok", "message": f"Document '{file_name}' supprimé."}


@app.post("/api/project/{project_id}/reindex")
async def reindex_project_files(project_id: str):
    """Re-index all .md, .txt, .json files in the project root (not system files)."""
    project_dir = PROJECTS_ROOT / project_id
    if not project_dir.exists():
        return {"status": "error", "message": "Projet introuvable."}

    SKIP = {"_config", "_uploads", "__pycache__", ".git"}
    SYSTEM_FILES = {"todos.json", "contacts.json", "MEMORY.md"}
    indexed = []

    for ext in (".md", ".txt", ".json"):
        for f in project_dir.rglob(f"*{ext}"):
            if any(part in SKIP for part in f.parts):
                continue
            if f.name in SYSTEM_FILES:
                continue
            try:
                delete_file_chunks(project_id, f.name)
                result = ingest_file(f, project_id)
                if result.get("status") == "ok":
                    indexed.append(f.name)
            except Exception as e:
                logger.warning(f"Reindex failed for {f.name}: {e}")

    return {
        "status": "ok",
        "indexed": indexed,
        "count": len(indexed),
        "message": f"{len(indexed)} fichier(s) indexé(s).",
    }


# ─── File access ─────────────────────────────────────────────

def _find_file_recursive(project_dir: Path, name: str) -> Path | None:
    """Search for a file by name recursively in the project (including _uploads).
    Handles macOS NFD/NFC Unicode normalization differences."""
    import unicodedata
    name_nfc = unicodedata.normalize("NFC", name)
    for p in project_dir.rglob("*"):
        if p.is_file() and unicodedata.normalize("NFC", p.name) == name_nfc:
            if not any(part.startswith(".") for part in p.relative_to(project_dir).parts):
                return p
    return None


@app.get("/api/project/{project_id}/file/{file_path:path}")
async def get_file(project_id: str, file_path: str):
    """Read a project file and return its content."""
    from fastapi.responses import JSONResponse

    project_dir = PROJECTS_ROOT / project_id
    target = (project_dir / file_path).resolve()

    if not str(target).startswith(str(project_dir.resolve())):
        return JSONResponse({"status": "error", "message": "Chemin hors projet."}, status_code=403)

    if not target.exists():
        found = _find_file_recursive(project_dir, Path(file_path).name)
        if found:
            target = found
        else:
            return JSONResponse({"status": "error", "message": f"Fichier '{file_path}' introuvable."}, status_code=404)

    real_path = str(target.relative_to(project_dir.resolve()))
    abs_path = str(target)

    if target.is_dir():
        entries = []
        for entry in sorted(target.iterdir()):
            if entry.name.startswith("."):
                continue
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None,
            })
        return {"type": "directory", "path": real_path, "abs_path": abs_path, "entries": entries}

    ext = target.suffix.lower()
    rich_exts = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".eml", ".msg"}

    if ext in rich_exts:
        try:
            from ingestion.extractor import extract
            text, meta = extract(target)
            return {
                "type": "file",
                "path": real_path,
                "abs_path": abs_path,
                "name": target.name,
                "extension": ext,
                "content": text[:100_000],
                "metadata": meta,
            }
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Extraction impossible : {e}"}, status_code=400)

    try:
        content = target.read_text(encoding="utf-8")
        return {
            "type": "file",
            "path": real_path,
            "abs_path": abs_path,
            "name": target.name,
            "extension": ext,
            "content": content[:100_000],
        }
    except UnicodeDecodeError:
        return JSONResponse({"status": "error", "message": "Fichier binaire non supporté."}, status_code=400)


@app.post("/api/open-in-finder")
async def open_in_finder(request: Request):
    """Open a file or folder in macOS Finder."""
    import subprocess
    body = await request.json()
    path = body.get("path", "")
    if not path:
        return {"status": "error", "message": "Chemin vide."}
    target = Path(path)
    if not target.exists():
        return {"status": "error", "message": "Fichier introuvable."}
    if not str(target.resolve()).startswith(str(PROJECTS_ROOT.resolve())):
        return {"status": "error", "message": "Chemin hors projet."}
    if target.is_dir():
        subprocess.Popen(["open", str(target)])
    else:
        subprocess.Popen(["open", "-R", str(target)])
    return {"status": "ok"}


@app.post("/api/open-file")
async def open_file(request: Request):
    """Open a file with the default macOS app (Preview for PDFs, etc.)."""
    import subprocess
    body = await request.json()
    path = body.get("path", "")
    if not path:
        return {"status": "error", "message": "Chemin vide."}
    target = Path(path)
    if not target.exists():
        return {"status": "error", "message": "Fichier introuvable."}
    if not str(target.resolve()).startswith(str(PROJECTS_ROOT.resolve())):
        return {"status": "error", "message": "Chemin hors projet."}
    subprocess.Popen(["open", str(target)])
    return {"status": "ok"}


@app.get("/api/project/{project_id}/tree")
async def get_tree(project_id: str):
    """List all files in the project recursively."""
    project_dir = PROJECTS_ROOT / project_id
    if not project_dir.exists():
        return {"files": []}

    files = []
    for p in sorted(project_dir.rglob("*")):
        if any(part.startswith(".") or part == "_uploads" for part in p.relative_to(project_dir).parts):
            continue
        if p.is_file():
            files.append(str(p.relative_to(project_dir)))
    return {"files": files}


# ─── MCP Servers ─────────────────────────────────────────────

@app.get("/api/mcp/servers")
async def list_mcp_servers():
    """List all configured MCP servers and their status."""
    return {"servers": mcp_servers_status()}


@app.post("/api/mcp/servers")
async def add_mcp_server(request: Request):
    """Add a new MCP server and connect to it."""
    body = await request.json()
    name = body.get("name", "").strip()
    command = body.get("command", "").strip()
    args = body.get("args", [])
    env = body.get("env", {})

    if not name:
        return {"status": "error", "message": "Le nom du serveur est requis."}
    if not command:
        return {"status": "error", "message": "La commande est requise."}

    configs = load_mcp_config()
    raw_servers = {
        n: {"command": c.command, "args": c.args, "env": c.env}
        for n, c in configs.items()
    }
    raw_servers[name] = {"command": command, "args": args, "env": env}
    save_mcp_config(raw_servers)

    config = MCPServerConfig(command=command, args=args, env=env)
    state = await connect_server(name, config)

    return {
        "status": "ok" if state.connected else "error",
        "server": {
            "name": name,
            "connected": state.connected,
            "tools_count": len(state.tools),
            "error": state.error,
        },
    }


@app.delete("/api/mcp/servers/{server_name}")
async def remove_mcp_server(server_name: str):
    """Disconnect and remove an MCP server."""
    await disconnect_server(server_name)

    configs = load_mcp_config()
    raw_servers = {
        n: {"command": c.command, "args": c.args, "env": c.env}
        for n, c in configs.items()
        if n != server_name
    }
    save_mcp_config(raw_servers)

    return {"status": "ok", "message": f"Serveur MCP '{server_name}' supprimé."}


@app.post("/api/mcp/servers/{server_name}/reconnect")
async def reconnect_mcp_server(server_name: str):
    """Reconnect to an MCP server."""
    configs = load_mcp_config()
    config = configs.get(server_name)
    if not config:
        return {"status": "error", "message": f"Serveur '{server_name}' non trouvé dans la config."}

    await disconnect_server(server_name)
    state = await connect_server(server_name, config)

    return {
        "status": "ok" if state.connected else "error",
        "connected": state.connected,
        "tools_count": len(state.tools),
        "error": state.error,
    }


@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """List all tools from connected MCP servers."""
    tools = get_mcp_tools()
    return {
        "tools": [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
            }
            for t in tools
        ],
        "total": len(tools),
    }


# ─── Providers / Multi-LLM ────────────────────────────────────

@app.get("/api/providers")
async def api_list_providers():
    """List all available LLM providers and their config status."""
    return {"providers": list_providers()}


@app.get("/api/project/{project_id}/model")
async def api_get_model(project_id: str):
    """Get the currently configured provider/model for a project."""
    from providers import get_project_model_config
    provider_id, model = get_project_model_config(project_id)
    return {"provider": provider_id, "model": model}


@app.put("/api/project/{project_id}/model")
async def api_set_model(project_id: str, request: Request):
    """Set the provider/model for a project."""
    body = await request.json()
    provider_id = body.get("provider", "deepseek")
    model = body.get("model", "deepseek-chat")
    save_project_model_config(project_id, provider_id, model)
    return {"status": "ok", "provider": provider_id, "model": model}


# ─── Conversations ───────────────────────────────────────────

@app.post("/api/project/{project_id}/conversations")
async def create_conv(project_id: str):
    ensure_project(project_id)
    conv_id = create_conversation(project_id)
    return {"conversation_id": conv_id}


@app.get("/api/project/{project_id}/conversations")
async def list_conv(project_id: str):
    convs = list_conversations(project_id)
    return {"conversations": convs}


@app.get("/api/conversations/{conv_id}")
async def get_conv(conv_id: str):
    conv = get_conversation(conv_id)
    if not conv:
        return {"status": "error", "message": "Conversation introuvable."}
    return conv


@app.put("/api/conversations/{conv_id}")
async def update_conv(conv_id: str, request: Request):
    body = await request.json()
    messages = body.get("messages")
    title = body.get("title")
    if messages is not None:
        save_conversation(conv_id, messages, title)
    return {"status": "ok"}


@app.delete("/api/conversations/{conv_id}")
async def delete_conv(conv_id: str):
    delete_conversation(conv_id)
    return {"status": "ok"}


# ─── Task Queue ──────────────────────────────────────────────

@app.get("/api/tasks")
async def api_list_tasks(project_id: str | None = None):
    return {"tasks": task_queue.list_tasks(project_id)}


@app.get("/api/tasks/{task_id}")
async def api_get_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        return {"status": "error", "message": "Tâche introuvable"}
    return task.to_dict()


@app.post("/api/tasks/{task_id}/cancel")
async def api_cancel_task(task_id: str):
    ok = task_queue.cancel_task(task_id)
    return {"status": "ok" if ok else "error"}


# ─── Daemon & Heartbeat ─────────────────────────────────────

@app.get("/api/daemon/status")
async def api_daemon_status():
    return {
        "pid": os.getpid(),
        "heartbeat": heartbeat.status(),
    }


@app.post("/api/daemon/heartbeat/toggle")
async def api_toggle_heartbeat():
    if heartbeat.is_running:
        await heartbeat.stop()
        return {"status": "stopped"}
    else:
        await heartbeat.start()
        return {"status": "started"}


@app.post("/api/shutdown")
async def api_shutdown():
    """Graceful daemon shutdown."""
    logger.info("Shutdown requested via API")
    asyncio.get_event_loop().call_later(1, lambda: os._exit(0))
    return {"status": "shutting_down"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=11434)
