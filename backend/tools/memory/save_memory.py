from datetime import datetime
from pathlib import Path
from tools._base import tool
from tools._registry import PROJECTS_ROOT


def _sync_memory_md(project_id: str):
    """Write a human-readable MEMORY.md mirror of SQLite memories."""
    from database import get_all_memories

    memories = get_all_memories(project_id)
    project_dir = PROJECTS_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    memory_file = project_dir / "MEMORY.md"

    lines = [
        "# Mémoire du projet",
        "",
        f"*Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y à %H:%M')}*",
        "",
    ]
    if memories:
        for m in memories:
            date = m.get("created_at", "")[:10]
            lines.append(f"- **{m['key']}** : {m['value']}  *(enregistré le {date})*")
    else:
        lines.append("*(aucune mémoire enregistrée)*")

    memory_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


@tool(
    name="save_to_long_term_memory",
    description=(
        "Sauvegarde ou supprime une mémoire persistante (préférence, info importante). "
        "QUAND l'utiliser : quand l'utilisateur exprime une préférence durable, donne une info à retenir, "
        "ou quand il CONTREDIT une mémoire existante (utilise action 'delete'). "
        "QUAND NE PAS l'utiliser : pour des infos ponctuelles qui ne servent qu'à la conversation en cours. "
        "Exemples : 'montants toujours en k€', 'le client principal est Omega Corp'."
    ),
    category="memory",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["save", "delete"],
                "description": "Action : 'save' pour créer/mettre à jour, 'delete' pour supprimer une mémoire obsolète ou contredite.",
            },
            "key": {
                "type": "string",
                "description": "Identifiant court de la mémoire (ex: 'format_montants', 'client_principal').",
            },
            "value": {
                "type": "string",
                "description": "Le contenu à mémoriser (requis pour 'save', ignoré pour 'delete').",
            },
        },
        "required": ["action", "key"],
    },
)
def save_to_long_term_memory(args: dict, project_id: str, project_dir: Path) -> str:
    from database import save_memory, delete_memory

    action = args.get("action", "save")
    key = args.get("key", "").strip()

    if not key:
        return "Erreur : La clé de mémoire est vide."

    if action == "delete":
        delete_memory(project_id, key)
        _sync_memory_md(project_id)
        return f"Mémoire '{key}' supprimée."

    value = args.get("value", "").strip()
    if not value:
        return "Erreur : La valeur à mémoriser est vide."

    save_memory(project_id, key, value)
    _sync_memory_md(project_id)
    return f"Mémorisé : '{key}' = '{value}'."
