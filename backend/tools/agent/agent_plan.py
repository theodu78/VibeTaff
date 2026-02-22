"""Internal agent planning tool — lets the LLM organise its own task list."""

import json
from pathlib import Path
from tools._base import tool

_current_plans: dict[str, list[dict]] = {}


def get_current_plan(project_id: str) -> list[dict]:
    return _current_plans.get(project_id, [])


def clear_plan(project_id: str):
    _current_plans.pop(project_id, None)


@tool(
    name="agent_plan",
    description=(
        "Crée ou met à jour ton plan de travail INTERNE (pas les tâches de l'utilisateur). "
        "QUAND l'utiliser : PROACTIVEMENT quand la demande nécessite 3 étapes ou plus. "
        "QUAND NE PAS l'utiliser : pour les tâches de l'utilisateur (utilise manage_todo), "
        "pour les actions simples de 1-2 étapes. "
        "RÈGLES : items de 14 mots max, commençant par un verbe. "
        "NE PAS inclure : recherches, lectures, vérifications — uniquement des tâches de haut niveau. "
        "Envoie la liste COMPLÈTE à chaque appel. Max 2-3 appels par message."
    ),
    category="agent",
    parameters={
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Liste complète des tâches du plan.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Identifiant court et unique (ex: 'step-1').",
                        },
                        "content": {
                            "type": "string",
                            "description": "Description courte de la tâche.",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "Statut actuel.",
                        },
                    },
                    "required": ["id", "content", "status"],
                },
            },
        },
        "required": ["todos"],
    },
)
def agent_plan(args: dict, project_id: str, project_dir: Path) -> str:
    todos = args.get("todos", [])
    if not todos:
        return "Erreur : la liste de tâches est vide."

    _current_plans[project_id] = todos

    done = sum(1 for t in todos if t.get("status") == "completed")
    total = len(todos)
    return (
        f"[PLAN_INTERNE] Plan mis à jour : {done}/{total} tâche(s) terminée(s). "
        "Le bloc visuel est affiché à l'utilisateur. "
        "Continue à travailler et mets à jour le plan après chaque tâche complétée."
    )
