from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="rename_project_file",
    description=(
        "Renomme ou déplace un fichier dans le projet. "
        "QUAND l'utiliser : quand l'utilisateur demande de renommer, déplacer ou réorganiser un fichier. "
        "Supporte les sous-dossiers (les dossiers seront créés automatiquement)."
    ),
    category="files",
    requires_approval=True,
    parameters={
        "type": "object",
        "properties": {
            "old_name": {
                "type": "string",
                "description": "Chemin relatif actuel du fichier (ex: 'brouillon.md').",
            },
            "new_name": {
                "type": "string",
                "description": "Nouveau chemin relatif du fichier (ex: 'rapport-final.md').",
            },
        },
        "required": ["old_name", "new_name"],
    },
)
def rename_project_file(args: dict, project_id: str, project_dir: Path) -> str:
    old_name = args.get("old_name", "").strip()
    new_name = args.get("new_name", "").strip()

    if not old_name:
        return "Erreur : L'ancien nom de fichier est vide."
    if not new_name:
        return "Erreur : Le nouveau nom de fichier est vide."

    old_target = resolve_safe_path(project_dir, old_name)
    new_target = resolve_safe_path(project_dir, new_name)

    if old_target is None:
        return f"Erreur : Le chemin '{old_name}' sort du périmètre du projet."
    if new_target is None:
        return f"Erreur : Le chemin '{new_name}' sort du périmètre du projet."

    if not old_target.exists():
        return f"Erreur : Le fichier '{old_name}' n'existe pas."

    if new_target.exists():
        return f"Erreur : Le fichier '{new_name}' existe déjà. Supprime-le d'abord ou choisis un autre nom."

    new_target.parent.mkdir(parents=True, exist_ok=True)
    old_target.rename(new_target)
    return f"'{old_name}' a été renommé en '{new_name}'."
