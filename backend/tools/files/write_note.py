from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="write_project_note",
    description="Crée ou écrase un fichier texte/markdown dans le projet. Utilisé pour les notes, brouillons et rapports.",
    category="files",
    requires_approval=True,
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Nom du fichier sans extension (ex: 'synthese', 'rapport-audit'). L'extension .md sera ajoutée automatiquement.",
            },
            "markdown_content": {
                "type": "string",
                "description": "Contenu Markdown du document.",
            },
        },
        "required": ["title", "markdown_content"],
    },
)
def write_project_note(args: dict, project_id: str, project_dir: Path) -> str:
    title = args.get("title", "")
    content = args.get("markdown_content", "")

    if not title:
        return "Erreur : Le titre du document est vide."

    safe_title = "".join(c for c in title if c.isalnum() or c in "-_ ").strip()
    if not safe_title:
        return "Erreur : Le titre ne contient aucun caractère valide."

    file_name = f"{safe_title}.md"
    target = resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le nom '{file_name}' n'est pas valide."

    target.write_text(content, encoding="utf-8")
    return f"Le fichier '{file_name}' a été créé avec succès ({len(content)} caractères)."
