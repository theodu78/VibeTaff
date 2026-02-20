# Plan V2 VibeTaff — Inspiré Open Claw

## Vue d'ensemble

5 phases indépendantes et livrables, inspirées de l'architecture d'Open Claw (187k+ stars GitHub, assistant IA personnel open-source).

| Phase | Nom | Effort | Ce que ça change | Pilier OpenClaw |
|---|---|---|---|---|
| **Phase 1** | Garde-fous & Mémoire | ~1 jour | Agent plus intelligent, moins de tokens gaspillés | Anti-Hallucination |
| **Phase 2** | Outils pluggables | ~2 jours | Architecture extensible, facile d'ajouter des outils | Skills / Prise USB |
| **Phase 3** | Client MCP | ~3 jours | Ouvre l'écosystème (Gmail, Calendar, Notion, Slack…) | Skills / Prise USB |
| **Phase 4** | Multi-LLM | ~2 jours | Changer de cerveau en 1 clic (DeepSeek, Claude, GPT, Mistral…) | Agnosticisme LLM |
| **Phase 5** | Daemon & Heartbeat | ~3 jours | L'agent vit en arrière-plan, travaille seul, notifie | Daemon Local |

---

## Phase 1 — Garde-fous & Mémoire (les "quick wins")

4 chantiers, tous dans le backend existant.

### 1A. Gating d'outils — Cacher ce qui n'est pas dispo

**Fichier touché :** `main.py`

Aujourd'hui, les 12 outils sont toujours envoyés au LLM, même si `TAVILY_API_KEY` n'est pas configurée. Résultat : l'agent essaie `web_search`, crash, et gaspille un step.

**Le changement :**
- Au démarrage de chaque requête `/api/chat`, filtrer `TOOL_DEFINITIONS` selon l'état réel :
  - Pas de `TAVILY_API_KEY` → retirer `web_search`
  - Aucun document indexé dans le projet → retirer `query_project_memory`
  - Pas de police unicode installée → retirer `export_to_pdf`
- Réduit le nombre de tokens du system prompt et empêche les erreurs bêtes

**Estimation :** 2h

---

### 1B. Détection de boucle intelligente

**Fichier touché :** `main.py` (dans la boucle `while steps < MAX_AGENT_STEPS`)

Aujourd'hui on a juste `MAX_AGENT_STEPS = 10`. L'agent peut boucler 10 fois sur le même outil avec les mêmes arguments avant d'être coupé.

**Le changement :**
- Garder un historique des derniers appels : `[(tool_name, args_hash)]`
- **Repeat detection :** si le même outil est appelé 2 fois avec les mêmes arguments → injecter un message système "Tu as déjà appelé cet outil avec ces arguments. Donne ta meilleure réponse avec ce que tu as."
- **Ping-pong detection :** si l'agent alterne entre 2 outils (A → B → A → B) → même injection
- Coupe les boucles à 2-3 steps au lieu de 10

**Estimation :** 2h

---

### 1C. Instructions par projet (le "AGENTS.md" de VibeTaff)

**Fichiers touchés :** `main.py` (`build_system_prompt`), `tools.py` (nouvel outil)

L'idée : chaque projet peut avoir un fichier `_config/instructions.md` qui s'ajoute au system prompt. L'utilisateur (ou l'agent) peut y écrire des consignes spécifiques.

**Le changement :**
- Dans `build_system_prompt()` : lire `~/VibetaffProjects/{project_id}/_config/instructions.md` si il existe, et l'ajouter au prompt
- Ajouter un nouvel outil `update_project_instructions` qui permet à l'agent de mettre à jour ce fichier quand l'utilisateur donne des consignes générales
- Exemple : l'utilisateur dit "Je veux toujours les montants en k€" → l'agent écrit ça dans instructions.md → c'est actif à chaque message

**Estimation :** 3h

---

### 1D. Mémoire structurée (MEMORY.md)

**Fichiers touchés :** `tools.py` (`_save_to_long_term_memory`), `main.py` (`build_system_prompt`)

Aujourd'hui la mémoire est dans SQLite (invisible). On garde SQLite, mais on ajoute un miroir lisible.

**Le changement :**
- Quand l'agent appelle `save_to_long_term_memory`, en plus de l'écriture SQLite, écrire/mettre à jour un fichier `MEMORY.md` à la racine du projet
- Format lisible par l'humain (Markdown avec date, catégorie, valeur)
- L'utilisateur peut ouvrir ce fichier et voir ce que l'agent a retenu
- Ajouter un outil `list_memories` pour que l'agent puisse consulter sa mémoire

**Estimation :** 2h

---

## Phase 2 — Outils pluggables (le refactoring)

L'idée : passer du gros `tools.py` monolithique à un système où chaque outil est un fichier Python séparé, découvert automatiquement.

### 2A. Nouvelle architecture fichiers ✅ FAIT

```
backend/
├── tools/
│   ├── __init__.py          # Auto-discovery + registry
│   ├── _base.py             # Décorateur @tool + classe ToolDefinition
│   ├── _registry.py         # Registre global + gating
│   ├── files/
│   │   ├── list_files.py
│   │   ├── read_file.py
│   │   ├── write_note.py
│   │   ├── write_json.py
│   │   ├── delete_file.py
│   │   ├── rename_file.py
│   │   └── export_pdf.py
│   ├── memory/
│   │   ├── query_memory.py
│   │   ├── save_memory.py
│   │   └── list_memories.py
│   ├── web/
│   │   ├── web_search.py
│   │   └── draft_email.py
│   ├── compute/
│   │   └── run_calculation.py
│   └── project/
│       ├── update_instructions.py
│       ├── manage_todo.py      ← NOUVEAU
│       └── save_meeting_note.py ← NOUVEAU
```

**Estimation :** 2h ✅

---

### 2B. Le décorateur `@tool` ✅ FAIT

Chaque outil sera un fichier simple avec un décorateur. Exemple :

```python
from tools._base import tool

@tool(
    name="web_search",
    description="Recherche sur le web via Tavily...",
    category="web",
    requires_env=["TAVILY_API_KEY"],
    parameters={...}
)
def web_search(args: dict, project_id: str) -> str:
    # ... le code actuel ...
```

Le décorateur gère :
- L'enregistrement dans le registre global
- Le gating automatique (vérifie `requires_env`, `requires_docs`, etc.)
- La génération de la définition OpenAI Tool Calling

**Estimation :** 3h ✅

---

### 2C. Le registre d'outils ✅ FAIT

`_registry.py` fournit :
- `get_available_tools(project_id)` → retourne uniquement les outils disponibles (après gating)
- `execute_tool(name, args, project_id)` → remplace le gros `if/elif`
- `list_tool_categories()` → pour le frontend (afficher les outils par catégorie)

**Estimation :** 3h ✅

---

### 2D. Migration des 12 outils existants ✅ FAIT

Déplacer chaque outil du monolithe `tools.py` vers son propre fichier dans la bonne catégorie. Pas de changement de logique, juste du découpage.

**Estimation :** 4h

---

### 2E. Impact sur `main.py` ✅ FAIT

L'import change de :

```python
# Avant
from tools import TOOL_DEFINITIONS, execute_tool

# Après
from tools import get_available_tools, execute_tool
```

Et dans la boucle agentique :

```python
tools = get_available_tools(project_id)  # filtré dynamiquement
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=openai_messages,
    tools=tools,  # au lieu de TOOL_DEFINITIONS constant
    ...
)
```

---

### 2F. Outil `manage_todo` — Gestion de tâches locale ✅ FAIT

**Fichier :** `tools/project/manage_todo.py`

Gère un fichier `todos.json` à la racine de chaque projet. L'utilisateur dit "note que je dois relancer Jean vendredi" et l'agent crée la tâche automatiquement.

**4 actions :** `add`, `update`, `delete`, `list`

**Structure du fichier `todos.json` :**

```json
[
  {"id": 1, "tache": "Relancer fournisseur X", "priorite": "haute", "deadline": "2026-02-25", "statut": "a_faire", "cree_le": "2026-02-20 14:30"},
  {"id": 2, "tache": "Vérifier facture Y", "priorite": "normale", "deadline": null, "statut": "fait", "cree_le": "2026-02-19 09:00"}
]
```

**Pas de validation requise** (pas `requires_approval`) car ajouter une tâche n'est pas destructeur. L'utilisateur peut lister et supprimer facilement.

---

### 2G. Outil `save_meeting_note` — Comptes-rendus de réunion ✅ FAIT

**Fichier :** `tools/project/save_meeting_note.py`

Crée un fichier Markdown structuré dans le dossier `reunions/` du projet. L'utilisateur dicte le contenu en vrac, l'agent structure.

**Nécessite approbation** (`requires_approval=True`) car il crée un fichier.

**Exemple de fichier généré (`reunions/2026-02-20-point-chantier.md`) :**

```markdown
# Point Chantier — 2026-02-20

**Participants** : Jean, Marie, Paul
**Durée** : 45 min

## Points abordés
- Retard livraison béton → relancer fournisseur
- Budget dépassé de 12k€ sur le lot plomberie

## Actions
- [ ] Relancer fournisseur béton (Jean, avant 25/02)
- [ ] Demander avenant au client (Paul)

## Notes complémentaires
Prochaine réunion prévue le 27/02.
```

---

### 2H. Stratégie gestion de projet — Local + Google Workspace

**Décision d'architecture :** la gestion de projet est séparée en deux couches.

**Couche locale (outils natifs VibeTaff) :**

| Besoin | Outil | Stockage |
|---|---|---|
| To-do / rappels | `manage_todo` | `todos.json` |
| Notes de réunion | `save_meeting_note` | `reunions/*.md` |
| Documents / rapports | `write_project_note` | `*.md` |
| Données tabulaires | `write_json_table` | `*.json` |

**Couche cloud (Phase 3, via MCP Google Workspace) :**

| Besoin | Service | Via |
|---|---|---|
| Mails | Gmail | MCP Google Workspace |
| Agenda / deadlines | Google Calendar | MCP Google Workspace |
| Partage de fichiers | Google Drive | MCP Google Workspace (optionnel) |

La couche locale fonctionne sans internet et sans compte tiers. La couche cloud s'ajoute en Phase 3 quand le client MCP sera prêt.

---

## Phase 3 — Client MCP (l'ouverture à l'écosystème)

L'idée : intégrer un client MCP dans le backend pour que l'utilisateur puisse brancher des serveurs d'outils externes (Gmail, Google Calendar, Notion, Slack…) sans écrire de code.

### 3A. Le client MCP dans FastAPI

**Nouvelle dépendance :** `mcp` (SDK Python officiel, v1.26+)

**Nouveau fichier :** `backend/mcp_client.py`

- Se connecte aux MCP servers configurés par l'utilisateur
- Récupère la liste de leurs outils (schéma JSON)
- Convertit chaque outil MCP au format OpenAI Tool Calling
- Les injecte dans le registre d'outils (Phase 2) comme outils dynamiques

**Estimation :** 4h

---

### 3B. Configuration MCP

**Nouveau fichier :** `~/VibetaffProjects/.mcp-config.json`

```json
{
  "servers": {
    "gmail": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-gmail"],
      "env": { "GOOGLE_CREDENTIALS": "..." }
    },
    "notion": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-notion"],
      "env": { "NOTION_TOKEN": "..." }
    }
  }
}
```

L'utilisateur ajoute des serveurs MCP via cette config. Au démarrage, le backend lance chaque serveur en subprocess et récupère ses outils.

**Estimation :** 3h

---

### 3C. Exécution des outils MCP

Quand le LLM appelle un outil MCP :
1. Le registre détecte que c'est un outil MCP (pas natif)
2. Il route l'appel vers le bon MCP server via le client
3. Le résultat est renvoyé au LLM normalement

C'est transparent pour le LLM — il ne sait pas si l'outil est natif ou MCP.

**Estimation :** 3h

---

### 3D. Endpoints API pour le frontend

- `GET /api/mcp/servers` → liste les serveurs configurés et leur état
- `POST /api/mcp/servers` → ajouter un serveur MCP
- `DELETE /api/mcp/servers/{name}` → supprimer un serveur
- `GET /api/mcp/tools` → liste tous les outils MCP disponibles

**Estimation :** 2h

---

### 3E. UI dans le frontend

- Page "Réglages" → onglet "Extensions MCP"
- Liste des serveurs connectés avec un indicateur vert/rouge
- Bouton "Ajouter un serveur MCP"
- Catalogue pré-configuré des serveurs populaires (Gmail, Calendar, Notion, Slack, Drive)

**Estimation :** 4h

---

---

## Phase 4 — Multi-LLM : "Bring Your Own Brain" (NOUVEAU)

> **Pilier OpenClaw couvert :** Agnosticisme LLM
> **Référence code source :** OpenClaw utilise des "provider adapters" dans `src/providers/` avec un pattern adapter + fallback chain. Chaque provider (OpenAI, Anthropic, Ollama, Google) a son propre fichier qui implémente la même interface `ChatProvider`.

### 4A. Abstraction Provider — `backend/providers/`

**Nouveau dossier :** `backend/providers/`

```
backend/providers/
├── __init__.py          # get_provider(name) → ChatProvider
├── _base.py             # Classe abstraite ChatProvider
├── deepseek.py          # Provider DeepSeek (actuel, extrait de main.py)
├── openai_compat.py     # Provider OpenAI / GPT-4o / GPT-5
├── anthropic.py         # Provider Claude (API Messages)
├── ollama.py            # Provider Ollama (modèles locaux)
└── mistral.py           # Provider Mistral
```

**La classe abstraite `ChatProvider` :**

```python
class ChatProvider(ABC):
    name: str
    supports_thinking: bool    # DeepSeek oui, GPT non
    supports_tool_calling: bool

    @abstractmethod
    async def create_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = True,
    ) -> AsyncIterator[CompletionChunk]:
        """Retourne un flux de chunks normalisés."""

    @abstractmethod
    def normalize_chunk(self, raw_chunk) -> CompletionChunk:
        """Convertit un chunk brut (format provider) en format interne."""
```

**Le `CompletionChunk` normalisé :**

```python
@dataclass
class CompletionChunk:
    text_delta: str | None = None
    reasoning_delta: str | None = None    # None si le provider ne supporte pas
    tool_calls: list[ToolCallDelta] | None = None
    finish_reason: str | None = None
```

C'est la clé : la boucle agent dans `main.py` ne voit que des `CompletionChunk`, jamais le format brut de DeepSeek ou Claude. On peut changer de cerveau sans toucher à la boucle.

**Estimation :** 4h

---

### 4B. Extraction du provider DeepSeek

**Fichier touché :** `main.py` → extraire vers `providers/deepseek.py`

Aujourd'hui dans `main.py` on a :

```python
client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
response = await client.chat.completions.create(
    model="deepseek-chat",
    extra_body={"thinking": {"type": "enabled"}},
    ...
)
# + parsing custom de reasoning_content via getattr(delta, "reasoning_content", None)
```

Tout ça part dans `providers/deepseek.py`. Le `extra_body` thinking, le parsing du `reasoning_content`, le `base_url` — tout est encapsulé. La boucle agent ne sait plus que c'est DeepSeek.

**Estimation :** 2h

---

### 4C. Provider OpenAI / GPT

**Nouveau fichier :** `providers/openai_compat.py`

Utilise le SDK `openai` standard (même que DeepSeek mais sans `extra_body`). Compatible avec :
- GPT-4o, GPT-4o-mini, GPT-5
- Tout endpoint compatible OpenAI (Groq, Together, etc.)

Pas de `reasoning_content` (GPT n'a pas de thinking mode visible) → `CompletionChunk.reasoning_delta` sera toujours `None`.

**Estimation :** 1h

---

### 4D. Provider Anthropic / Claude

**Nouveau fichier :** `providers/anthropic.py`
**Nouvelle dépendance :** `anthropic` (SDK Python officiel)

L'API Anthropic utilise un format Messages différent d'OpenAI :
- Pas de `role: system` → le system prompt va dans un paramètre `system` séparé
- Les tool results ont un format `tool_result` au lieu de `role: tool`
- Le streaming utilise des events `content_block_delta` au lieu de `choices[0].delta`
- Claude a un mode "extended thinking" → mapper vers `reasoning_delta`

Le provider `anthropic.py` gère cette traduction. La boucle agent ne voit que des `CompletionChunk`.

**Estimation :** 3h

---

### 4E. Provider Ollama (modèles locaux)

**Nouveau fichier :** `providers/ollama.py`

Ollama expose une API compatible OpenAI sur `http://localhost:11434/v1/`. Le provider est quasi identique à `openai_compat.py` mais avec :
- `base_url = "http://localhost:11434/v1/"`
- Pas de clé API
- Détection automatique : ping `http://localhost:11434/api/tags` pour lister les modèles installés
- Si Ollama n'est pas lancé → le provider se désactive proprement

**Estimation :** 1h

---

### 4F. Sélecteur de modèle dans le frontend

**Fichiers touchés :** `Settings.tsx`, `App.tsx`, `Chat.tsx`

**Nouveau endpoint :** `GET /api/providers` → liste les providers disponibles avec leurs modèles

```json
{
  "providers": [
    {"id": "deepseek", "name": "DeepSeek", "models": ["deepseek-chat", "deepseek-reasoner"], "configured": true},
    {"id": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini"], "configured": false},
    {"id": "anthropic", "name": "Claude", "models": ["claude-sonnet-4-20250514"], "configured": false},
    {"id": "ollama", "name": "Ollama (local)", "models": ["llama3", "mistral"], "configured": true}
  ]
}
```

**UI :**
- Menu déroulant dans le header (à côté de "+ Nouveau") pour changer de modèle en 1 clic
- Pastille verte/grise selon si le provider est configuré (clé API présente)
- Le choix est sauvegardé par projet dans `_config/model.json`
- Page Settings : champs pour entrer les clés API de chaque provider

**Nouveau dans `.env` :**

```
DEEPSEEK_API_KEY=sk-...       # (existant)
OPENAI_API_KEY=sk-...          # (optionnel)
ANTHROPIC_API_KEY=sk-ant-...   # (optionnel)
```

**Estimation :** 4h

---

### 4G. Fallback chain (bonus)

**Fichier touché :** `providers/__init__.py`

Si le provider principal échoue (rate limit, timeout, erreur 500), basculer automatiquement sur le suivant :

```python
FALLBACK_CHAIN = ["deepseek", "openai", "anthropic", "ollama"]

async def create_completion_with_fallback(provider_id, messages, tools):
    chain = [provider_id] + [p for p in FALLBACK_CHAIN if p != provider_id]
    for pid in chain:
        provider = get_provider(pid)
        if not provider or not provider.is_configured():
            continue
        try:
            return provider.create_completion(messages, tools)
        except ProviderError:
            log.warning(f"Provider {pid} failed, trying next...")
    raise AllProvidersFailed()
```

Le user voit un message dans le chat : "⚠️ DeepSeek indisponible, basculement sur Claude."

**Estimation :** 2h

---

## Phase 5 — Daemon & Heartbeat : "L'OS dans l'OS" (NOUVEAU)

> **Pilier OpenClaw couvert :** Daemon Local
> **Référence code source :** OpenClaw utilise un fichier `~/.openclaw/HEARTBEAT.md` qui contient les instructions du heartbeat en Markdown. Un cron interne (`setInterval`) exécute ces instructions à intervalle régulier. Le processus tourne en daemon via `src/daemon/index.ts` indépendamment de l'UI.

### 5A. Découplage Backend / Frontend

**Fichiers touchés :** `src-tauri/src/lib.rs`, `backend/main.py`

Aujourd'hui le backend FastAPI est lancé comme sidecar Tauri — il meurt quand la fenêtre se ferme.

**Le changement :**
- Le backend se lance comme un **service indépendant** (pas un sidecar)
- Au démarrage de Tauri : vérifier si le backend tourne déjà (`GET /api/health`). Si oui, s'y connecter. Sinon, le lancer.
- À la fermeture de Tauri : ne PAS tuer le backend. Il continue de tourner.
- Ajouter un endpoint `POST /api/shutdown` pour un arrêt propre (déclenché manuellement)
- Le backend écrit son PID dans `~/.vibetaff/daemon.pid` pour être retrouvé

**Impact Tauri (`lib.rs`) :**

```rust
// Au setup, au lieu de spawn sidecar :
// 1. Check si le backend répond sur :11434
// 2. Si oui → connecté, rien à lancer
// 3. Si non → lancer le binaire en background (pas sidecar)
//    et écrire le PID dans ~/.vibetaff/daemon.pid
```

**Estimation :** 3h

---

### 5B. File d'attente de tâches (Task Queue)

**Nouveau fichier :** `backend/task_queue.py`

Aujourd'hui chaque requête `/api/chat` est traitée en temps réel, de bout en bout. Si l'utilisateur ferme le navigateur pendant que l'agent travaille, tout est perdu.

**Le changement :**

```python
from dataclasses import dataclass, field
from enum import Enum
import asyncio

class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"       # En attente d'approbation humaine

@dataclass
class Task:
    id: str
    project_id: str
    conversation_id: str
    messages: list[dict]
    status: TaskStatus = TaskStatus.QUEUED
    result: str | None = None
    progress: dict = field(default_factory=dict)
    created_at: float = 0
    started_at: float | None = None
    completed_at: float | None = None

class TaskQueue:
    def __init__(self):
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._worker_task: asyncio.Task | None = None

    async def submit(self, task: Task) -> str:
        """Soumet une tâche et retourne son ID."""
        self._tasks[task.id] = task
        await self._queue.put(task)
        return task.id

    async def get_status(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    async def _worker(self):
        """Boucle de travail — tourne en permanence."""
        while True:
            task = await self._queue.get()
            task.status = TaskStatus.RUNNING
            try:
                await self._execute_task(task)
                task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.result = str(e)
```

**Nouveaux endpoints :**
- `GET /api/tasks` → liste les tâches en cours/terminées
- `GET /api/tasks/{task_id}` → statut d'une tâche
- `POST /api/tasks/{task_id}/cancel` → annuler une tâche

Le `/api/chat` existant continue de fonctionner en streaming pour le mode interactif. La task queue est pour les tâches longues lancées par le heartbeat ou en batch.

**Estimation :** 4h

---

### 5C. Heartbeat — Le cron de l'agent

**Nouveau fichier :** `backend/heartbeat.py`
**Nouveau fichier projet :** `~/VibetaffProjects/{project_id}/_config/HEARTBEAT.md`

Inspiré directement d'OpenClaw : un fichier Markdown qui décrit ce que l'agent doit faire automatiquement à intervalle régulier.

**Exemple de `HEARTBEAT.md` :**

```markdown
# Heartbeat — Tâches automatiques

## Toutes les 30 minutes
- Vérifie si de nouveaux fichiers ont été déposés dans _uploads/ et indexe-les automatiquement

## Tous les jours à 8h
- Fais un résumé des documents modifiés hier et écris-le dans journal/YYYY-MM-DD.md

## Quand un nouveau fichier est indexé
- Lis le fichier et mets à jour MEMORY.md avec les informations clés
```

**Implémentation :**

```python
import asyncio
from datetime import datetime

class Heartbeat:
    def __init__(self, interval_seconds: int = 1800):
        self.interval = interval_seconds
        self._running = False

    async def start(self):
        self._running = True
        while self._running:
            await self._tick()
            await asyncio.sleep(self.interval)

    async def _tick(self):
        """Exécute un cycle de heartbeat."""
        for project_id in self._list_projects():
            heartbeat_file = PROJECTS_ROOT / project_id / "_config" / "HEARTBEAT.md"
            if not heartbeat_file.exists():
                continue
            instructions = heartbeat_file.read_text()
            # Soumettre à la task queue comme un message système
            task = Task(
                id=f"heartbeat_{project_id}_{datetime.now().isoformat()}",
                project_id=project_id,
                messages=[{"role": "user", "content": f"[HEARTBEAT] {instructions}"}],
            )
            await task_queue.submit(task)

    async def stop(self):
        self._running = False
```

**Estimation :** 3h

---

### 5D. Notifications macOS

**Fichier touché :** `backend/main.py` (au démarrage) + nouveau `backend/notify.py`

Quand une tâche de fond se termine (heartbeat ou tâche longue), envoyer une notification macOS native.

```python
import subprocess

def notify(title: str, message: str):
    """Envoie une notification macOS via osascript."""
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)
```

Appelé quand :
- Une tâche de la task queue se termine
- Un heartbeat trouve quelque chose d'important
- Un document est indexé en arrière-plan

**Estimation :** 1h

---

### 5E. UI du Daemon dans le frontend

**Fichiers touchés :** `App.tsx` (header), nouveau `DaemonStatus.tsx`

**Indicateur dans le header :**
- Pastille verte : daemon actif, heartbeat ON
- Pastille orange : daemon actif, heartbeat OFF
- Pastille rouge : daemon hors ligne

**Panel "Tâches en cours" (accessible depuis le header) :**
- Liste des tâches actives/récentes
- Statut (en cours, terminé, échoué)
- Bouton pause/annuler
- Logs de la dernière exécution heartbeat

**Estimation :** 3h

---

## Planning recommandé

```
Semaine 1 : Phase 1 (quick wins)
├── 1A. Gating d'outils          (2h)
├── 1B. Détection de boucle      (2h)
├── 1C. Instructions par projet  (3h)
└── 1D. Mémoire structurée       (2h)

Semaine 2 : Phase 2 (refactoring outils)
├── 2A. Structure fichiers       (2h) ✅
├── 2B. Décorateur @tool         (3h) ✅
├── 2C. Registre + gating        (3h) ✅
├── 2D. Migration des 12 outils  (4h) ✅
├── 2E. Impact main.py           (1h) ✅
├── 2F. Outil manage_todo        (2h) ✅
├── 2G. Outil save_meeting_note  (1h) ✅
└── 2H. Stratégie locale/cloud   (doc)

Semaine 3 : Phase 3 (MCP + Google Workspace)
├── 3A. Client MCP               (4h)
├── 3B. Config + lifecycle       (3h)
├── 3C. Routing des appels       (3h)
├── 3D. Endpoints API            (2h)
├── 3E. UI frontend              (4h)
└── 3F. Google Workspace MCP     (3h) ← premier MCP branché

Semaine 4 : Phase 4 (Multi-LLM)
├── 4A. Abstraction Provider     (4h)
├── 4B. Extract DeepSeek         (2h)
├── 4C. Provider OpenAI          (1h)
├── 4D. Provider Anthropic       (3h)
├── 4E. Provider Ollama          (1h)
├── 4F. UI sélecteur modèle      (4h)
└── 4G. Fallback chain           (2h)

Semaine 5 : Phase 5 (Daemon)
├── 5A. Découplage backend       (3h)
├── 5B. Task Queue               (4h)
├── 5C. Heartbeat                (3h)
├── 5D. Notifications macOS      (1h)
└── 5E. UI Daemon                (3h)
```

---

## Audit comparatif : état actuel vs cible V2

| Aspect | V1 (actuel) | V2 (cible) | Inspiré de |
|---|---|---|---|
| Outils | ~~12 outils codés en dur~~ 16 outils pluggables, auto-découverts | + manage_todo, save_meeting_note | OpenClaw `tool groups` |
| Gating | ~~Aucun~~ ✅ gating dynamique | Outils masqués si prérequis manquants | OpenClaw `requires.env/bins` |
| Anti-boucle | `MAX_AGENT_STEPS = 10` | Détection repeat + ping-pong + max steps | OpenClaw `pingPong/genericRepeat` |
| Mémoire | SQLite clé/valeur invisible | SQLite + MEMORY.md lisible par l'humain | OpenClaw `~/.openclaw/memory/MEMORY.md` |
| Prompt projet | String fixe dans main.py | instructions.md configurable par projet | OpenClaw `AGENTS.md` / `SOUL.md` |
| Extensibilité | Zéro | Client MCP + registre dynamique | OpenClaw `mcporter` + ClawHub |
| Gestion projet | Inexistant | `manage_todo` + `save_meeting_note` locaux | Stratégie local-first |
| Mail/Agenda | `draft_email` basique | Google Workspace MCP (Gmail + Calendar) | MCP standard |
| Multi-LLM | DeepSeek câblé en dur | Provider adapters + fallback chain + menu déroulant | OpenClaw `src/providers/` + hub-and-spoke |
| Daemon | Backend meurt avec la fenêtre | Service indépendant + task queue + PID file | OpenClaw `src/daemon/` + heartbeat loop |
| Heartbeat | Inexistant | HEARTBEAT.md + cron interne + notifications | OpenClaw `~/.openclaw/HEARTBEAT.md` |
| Notifications | Inexistant | Notifications macOS natives | OpenClaw lifecycle events |
