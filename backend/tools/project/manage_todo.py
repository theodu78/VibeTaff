import json
from pathlib import Path
from datetime import datetime
from tools._base import tool, resolve_safe_path

TODOS_FILE = "todos.json"


def _load_todos(project_dir: Path) -> list[dict]:
    target = project_dir / TODOS_FILE
    if not target.exists():
        return []
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_todos(project_dir: Path, todos: list[dict]):
    target = project_dir / TODOS_FILE
    target.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_id(todos: list[dict]) -> int:
    if not todos:
        return 1
    return max(t.get("id", 0) for t in todos) + 1


@tool(
    name="manage_todo",
    description=(
        "Gère la liste de tâches (to-do) de l'UTILISATEUR. "
        "Actions : 'add', 'update', 'delete', 'list'. "
        "QUAND l'utiliser : quand l'utilisateur dit 'note que je dois...', 'ajoute une tâche', "
        "'rappelle-moi de...', 'qu'est-ce que j'ai à faire ?'. "
        "QUAND NE PAS l'utiliser : pour le plan de travail INTERNE de l'agent — utilise agent_plan. "
        "Après 'list', un bloc visuel s'affiche — ne reproduis PAS la liste en texte."
    ),
    category="project",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "update", "delete", "list"],
                "description": "L'action à effectuer.",
            },
            "tache": {
                "type": "string",
                "description": "Description de la tâche (pour 'add').",
            },
            "priorite": {
                "type": "string",
                "enum": ["haute", "normale", "basse"],
                "description": "Priorité de la tâche (pour 'add' ou 'update'). Par défaut 'normale'.",
            },
            "deadline": {
                "type": "string",
                "description": "Date limite au format YYYY-MM-DD (pour 'add' ou 'update'). Optionnel.",
            },
            "statut": {
                "type": "string",
                "enum": ["a_faire", "en_cours", "fait", "annule"],
                "description": "Statut de la tâche (pour 'update'). Par défaut 'a_faire'.",
            },
            "task_id": {
                "type": "integer",
                "description": "ID de la tâche (pour 'update' ou 'delete').",
            },
        },
        "required": ["action"],
    },
)
def manage_todo(args: dict, project_id: str, project_dir: Path) -> str:
    action = args.get("action", "")
    todos = _load_todos(project_dir)

    if action == "list":
        if not todos:
            return "Aucune tâche dans la liste."
        done = sum(1 for t in todos if t.get("statut") in ("fait", "annule"))
        pending = len(todos) - done
        return f"[AFFICHAGE_VISUEL] {len(todos)} tâche(s) affichée(s) dans le bloc interactif ({done} terminée(s), {pending} en attente). Ne reproduis PAS la liste, l'utilisateur la voit déjà."

    if action == "add":
        tache = args.get("tache", "").strip()
        if not tache:
            return "Erreur : la description de la tâche est vide."
        new_todo = {
            "id": _next_id(todos),
            "tache": tache,
            "priorite": args.get("priorite", "normale"),
            "deadline": args.get("deadline"),
            "statut": "a_faire",
            "cree_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        todos.append(new_todo)
        _save_todos(project_dir, todos)
        return f"Tâche #{new_todo['id']} ajoutée : « {tache} » (priorité {new_todo['priorite']})."

    if action == "update":
        task_id = args.get("task_id")
        if task_id is None:
            return "Erreur : 'task_id' est requis pour modifier une tâche."
        target = next((t for t in todos if t["id"] == task_id), None)
        if not target:
            return f"Erreur : tâche #{task_id} introuvable."
        changed = []
        if "statut" in args:
            target["statut"] = args["statut"]
            changed.append(f"statut → {args['statut']}")
        if "priorite" in args:
            target["priorite"] = args["priorite"]
            changed.append(f"priorité → {args['priorite']}")
        if "deadline" in args:
            target["deadline"] = args["deadline"]
            changed.append(f"deadline → {args['deadline']}")
        if "tache" in args:
            target["tache"] = args["tache"]
            changed.append(f"description → {args['tache']}")
        if not changed:
            return f"Aucune modification apportée à la tâche #{task_id}."
        target["modifie_le"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _save_todos(project_dir, todos)
        return f"Tâche #{task_id} mise à jour : {', '.join(changed)}."

    if action == "delete":
        task_id = args.get("task_id")
        if task_id is None:
            return "Erreur : 'task_id' est requis pour supprimer une tâche."
        before = len(todos)
        todos = [t for t in todos if t["id"] != task_id]
        if len(todos) == before:
            return f"Erreur : tâche #{task_id} introuvable."
        _save_todos(project_dir, todos)
        return f"Tâche #{task_id} supprimée."

    return f"Erreur : action '{action}' non reconnue. Utilisez 'add', 'update', 'delete' ou 'list'."
