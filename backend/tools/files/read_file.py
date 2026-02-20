from pathlib import Path
from tools._base import tool, resolve_safe_path, list_dir

RICH_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".eml", ".msg"}
MAX_CHARS = 50_000


def _extract_rich(file_path: Path) -> str:
    """Extract text from PDF, Word, Excel, CSV and email files."""
    from ingestion.extractor import extract
    text, _ = extract(file_path)
    return text


@tool(
    name="read_file_content",
    description="Lit le contenu d'un fichier du projet (texte, PDF, Word, Excel, CSV, email). Renvoie le texte extrait.",
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "Chemin relatif du fichier à lire (ex: 'notes.md', '_uploads/rapport.pdf')",
            }
        },
        "required": ["file_name"],
    },
)
def read_file_content(args: dict, project_id: str, project_dir: Path) -> str:
    file_name = args.get("file_name", "")
    if not file_name:
        return f"Erreur : Aucun nom de fichier fourni. Voici les fichiers du projet : {list_dir(project_dir)}"

    target = resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le chemin '{file_name}' sort du périmètre du projet."

    if not target.exists():
        return f"Erreur : Le fichier '{file_name}' n'existe pas. Voici les fichiers du projet : {list_dir(project_dir)}"

    if target.is_dir():
        return f"Erreur : '{file_name}' est un dossier, pas un fichier. Utilise list_project_files pour le lister."

    ext = target.suffix.lower()

    if ext in RICH_EXTENSIONS:
        try:
            content = _extract_rich(target)
            if len(content) > MAX_CHARS:
                content = content[:MAX_CHARS] + "\n\n... (fichier tronqué à 50 000 caractères)"
            return content
        except Exception as e:
            return f"Erreur lors de l'extraction de '{file_name}' : {e}"

    try:
        content = target.read_text(encoding="utf-8")
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n\n... (fichier tronqué à 50 000 caractères)"
        return content
    except UnicodeDecodeError:
        return f"Erreur : Le fichier '{file_name}' est un format binaire non supporté."
