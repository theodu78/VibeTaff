from pathlib import Path
from tools._base import tool


@tool(
    name="update_project_instructions",
    description=(
        "Met à jour les instructions permanentes du projet (appliquées à chaque message). "
        "QUAND l'utiliser : quand l'utilisateur donne une consigne générale pour le projet entier "
        "(ex: 'les montants en k€', 'le client s'appelle Omega'). "
        "QUAND NE PAS l'utiliser : pour une préférence personnelle durable — utilise save_to_long_term_memory. "
        "ATTENTION : le contenu REMPLACE les instructions existantes — inclure les anciennes + les nouvelles."
    ),
    category="project",
    parameters={
        "type": "object",
        "properties": {
            "instructions": {
                "type": "string",
                "description": "Le contenu Markdown complet des instructions du projet. Inclure toutes les instructions existantes + les nouvelles.",
            },
        },
        "required": ["instructions"],
    },
)
def update_project_instructions(args: dict, project_id: str, project_dir: Path) -> str:
    instructions = args.get("instructions", "").strip()
    if not instructions:
        return "Erreur : Le contenu des instructions est vide."

    config_dir = project_dir / "_config"
    config_dir.mkdir(exist_ok=True)
    target = config_dir / "instructions.md"
    target.write_text(instructions, encoding="utf-8")
    return f"Instructions du projet mises à jour ({len(instructions)} caractères). Elles seront appliquées automatiquement à chaque message."
