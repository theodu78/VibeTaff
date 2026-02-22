import shutil
from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="delete_project_file",
    description=(
        "Supprime un fichier ou dossier du projet. Action irréversible, nécessite confirmation. "
        "QUAND l'utiliser : quand l'utilisateur demande explicitement de supprimer un fichier. "
        "QUAND NE PAS l'utiliser : ne JAMAIS supprimer spontanément — toujours sur demande explicite."
    ),
    category="files",
    requires_approval=True,
    parameters={
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "Chemin relatif du fichier à supprimer (ex: 'brouillon.md', 'data/ancien.json').",
            },
        },
        "required": ["file_name"],
    },
)
def delete_project_file(args: dict, project_id: str, project_dir: Path) -> str:
    file_name = args.get("file_name", "").strip()
    if not file_name:
        return "Erreur : Aucun nom de fichier fourni."

    target = resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le chemin '{file_name}' sort du périmètre du projet."

    if not target.exists():
        return f"Erreur : Le fichier '{file_name}' n'existe pas."

    if target.is_dir():
        shutil.rmtree(target)
        return f"Le dossier '{file_name}' et son contenu ont été supprimés."

    target.unlink()
    return f"Le fichier '{file_name}' a été supprimé."
