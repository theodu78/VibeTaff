import os
import json
from pathlib import Path

PROJECTS_ROOT = Path.home() / "VibetaffProjects"

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_project_files",
            "description": "Liste les fichiers et dossiers présents dans le répertoire du projet. Utilise un chemin relatif depuis la racine du projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Chemin relatif du dossier à lister (ex: '.' pour la racine, 'sous-dossier/' pour un sous-dossier)",
                    }
                },
                "required": ["directory_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Lit le contenu texte d'un fichier du projet. Renvoie le contenu brut du fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_name": {
                        "type": "string",
                        "description": "Chemin relatif du fichier à lire (ex: 'notes.md', 'data/rapport.txt')",
                    }
                },
                "required": ["file_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_project_note",
            "description": "Crée ou écrase un fichier texte/markdown dans le projet. Utilisé pour les notes, brouillons et rapports.",
            "parameters": {
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
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_json_table",
            "description": "Crée un fichier JSON contenant un tableau de données structuré. Utilisé pour sauvegarder des tableaux, listes et données tabulaires.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Nom du fichier sans extension (ex: 'comparatif-prix', 'liste-fournisseurs'). L'extension .json sera ajoutée automatiquement.",
                    },
                    "json_data": {
                        "type": "array",
                        "description": "Tableau d'objets JSON représentant les lignes du tableau.",
                        "items": {"type": "object"},
                    },
                },
                "required": ["table_name", "json_data"],
            },
        },
    },
]


def _resolve_safe_path(project_dir: Path, relative_path: str) -> Path | None:
    """Resolve a path and verify it stays inside the project jail."""
    try:
        target = (project_dir / relative_path).resolve()
        project_resolved = project_dir.resolve()
        if not str(target).startswith(str(project_resolved)):
            return None
        return target
    except (ValueError, OSError):
        return None


def _ensure_project_dir(project_id: str = "default") -> Path:
    project_dir = PROJECTS_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def execute_tool(
    tool_name: str, arguments: dict, project_id: str = "default"
) -> str:
    """Execute a tool and return the result as a string for the LLM."""
    project_dir = _ensure_project_dir(project_id)

    try:
        if tool_name == "list_project_files":
            return _list_project_files(project_dir, arguments)
        elif tool_name == "read_file_content":
            return _read_file_content(project_dir, arguments)
        elif tool_name == "write_project_note":
            return _write_project_note(project_dir, arguments)
        elif tool_name == "write_json_table":
            return _write_json_table(project_dir, arguments)
        else:
            return f"Erreur : L'outil '{tool_name}' n'existe pas. Outils disponibles : list_project_files, read_file_content, write_project_note, write_json_table."
    except Exception as e:
        return f"Erreur système lors de l'exécution de '{tool_name}' : {str(e)}"


def _list_project_files(project_dir: Path, args: dict) -> str:
    dir_path = args.get("directory_path", ".")
    target = _resolve_safe_path(project_dir, dir_path)

    if target is None:
        return f"Erreur : Le chemin '{dir_path}' sort du périmètre du projet. Utilise un chemin relatif comme '.' ou 'sous-dossier/'."

    if not target.exists():
        return f"Erreur : Le dossier '{dir_path}' n'existe pas. Voici les fichiers à la racine du projet : {_list_dir(project_dir)}"

    if not target.is_dir():
        return f"Erreur : '{dir_path}' n'est pas un dossier, c'est un fichier. Utilise read_file_content pour le lire."

    return _list_dir(target)


def _list_dir(directory: Path) -> str:
    entries = sorted(directory.iterdir())
    if not entries:
        return "(dossier vide)"
    lines = []
    for entry in entries:
        if entry.name.startswith("."):
            continue
        prefix = "📁 " if entry.is_dir() else "📄 "
        size = ""
        if entry.is_file():
            size_bytes = entry.stat().st_size
            if size_bytes < 1024:
                size = f" ({size_bytes} o)"
            elif size_bytes < 1024 * 1024:
                size = f" ({size_bytes // 1024} Ko)"
            else:
                size = f" ({size_bytes // (1024 * 1024)} Mo)"
        lines.append(f"{prefix}{entry.name}{size}")
    return "\n".join(lines) if lines else "(dossier vide)"


def _read_file_content(project_dir: Path, args: dict) -> str:
    file_name = args.get("file_name", "")
    if not file_name:
        return f"Erreur : Aucun nom de fichier fourni. Voici les fichiers du projet : {_list_dir(project_dir)}"

    target = _resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le chemin '{file_name}' sort du périmètre du projet."

    if not target.exists():
        return f"Erreur : Le fichier '{file_name}' n'existe pas. Voici les fichiers du projet : {_list_dir(project_dir)}"

    if target.is_dir():
        return f"Erreur : '{file_name}' est un dossier, pas un fichier. Utilise list_project_files pour le lister."

    try:
        content = target.read_text(encoding="utf-8")
        if len(content) > 50_000:
            content = content[:50_000] + "\n\n... (fichier tronqué à 50 000 caractères)"
        return content
    except UnicodeDecodeError:
        return f"Erreur : Le fichier '{file_name}' n'est pas un fichier texte lisible (binaire)."


def _write_project_note(project_dir: Path, args: dict) -> str:
    title = args.get("title", "")
    content = args.get("markdown_content", "")

    if not title:
        return "Erreur : Le titre du document est vide."

    safe_title = "".join(c for c in title if c.isalnum() or c in "-_ ").strip()
    if not safe_title:
        return "Erreur : Le titre ne contient aucun caractère valide."

    file_name = f"{safe_title}.md"
    target = _resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le nom '{file_name}' n'est pas valide."

    target.write_text(content, encoding="utf-8")
    return f"Le fichier '{file_name}' a été créé avec succès ({len(content)} caractères)."


def _write_json_table(project_dir: Path, args: dict) -> str:
    table_name = args.get("table_name", "")
    json_data = args.get("json_data", [])

    if not table_name:
        return "Erreur : Le nom du tableau est vide."

    safe_name = "".join(c for c in table_name if c.isalnum() or c in "-_ ").strip()
    if not safe_name:
        return "Erreur : Le nom ne contient aucun caractère valide."

    file_name = f"{safe_name}.json"
    target = _resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le nom '{file_name}' n'est pas valide."

    target.write_text(
        json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    row_count = len(json_data) if isinstance(json_data, list) else 0
    return f"Le tableau '{file_name}' a été créé avec succès ({row_count} lignes)."
