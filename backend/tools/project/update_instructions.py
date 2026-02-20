from pathlib import Path
from tools._base import tool


@tool(
    name="update_project_instructions",
    description="Met à jour les instructions permanentes du projet. Ces instructions seront appliquées automatiquement à chaque message. Utilise cet outil quand l'utilisateur donne une consigne générale qui doit s'appliquer à tout le projet (ex: 'les montants doivent toujours être en k€', 'le client s'appelle Omega Corp').",
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
