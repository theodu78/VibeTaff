from pathlib import Path
from tools._base import tool


@tool(
    name="list_memories",
    description=(
        "Liste toutes les mémoires persistantes du projet (préférences, infos mémorisées). "
        "QUAND l'utiliser : pour vérifier ce qui est déjà mémorisé avant d'ajouter un doublon, "
        "ou quand l'utilisateur demande 'qu'est-ce que tu sais de moi ?'. "
        "QUAND NE PAS l'utiliser : les mémoires sont déjà injectées dans ton contexte à chaque message, "
        "tu n'as PAS besoin de les relire sauf si l'utilisateur le demande explicitement."
    ),
    category="memory",
    parameters={
        "type": "object",
        "properties": {},
    },
)
def list_memories(args: dict, project_id: str, project_dir: Path) -> str:
    from database import get_all_memories

    memories = get_all_memories(project_id)
    if not memories:
        return "Aucune mémoire enregistrée pour ce projet."

    parts = []
    for m in memories:
        date = m.get("created_at", "")[:10]
        parts.append(f"- {m['key']} : {m['value']} (enregistré le {date})")
    return f"{len(memories)} mémoire(s) enregistrée(s) :\n" + "\n".join(parts)
