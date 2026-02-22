from pathlib import Path
from tools._base import tool, resolve_safe_path, list_dir


@tool(
    name="list_project_files",
    description=(
        "Liste les fichiers et dossiers d'un répertoire du projet. "
        "QUAND l'utiliser : pour découvrir la structure du projet, vérifier qu'un fichier existe, "
        "ou quand l'utilisateur demande 'montre-moi mes fichiers'. "
        "QUAND NE PAS l'utiliser : pour chercher une info dans les documents — utilise "
        "query_project_memory à la place, c'est instantané et plus pertinent."
    ),
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "directory_path": {
                "type": "string",
                "description": "Chemin relatif du dossier à lister (ex: '.' pour la racine, 'sous-dossier/' pour un sous-dossier)",
            }
        },
        "required": ["directory_path"],
    },
)
def list_project_files(args: dict, project_id: str, project_dir: Path) -> str:
    dir_path = args.get("directory_path", ".")
    target = resolve_safe_path(project_dir, dir_path)

    if target is None:
        return f"Erreur : Le chemin '{dir_path}' sort du périmètre du projet. Utilise un chemin relatif comme '.' ou 'sous-dossier/'."

    if not target.exists():
        return f"Erreur : Le dossier '{dir_path}' n'existe pas. Voici les fichiers à la racine du projet : {list_dir(project_dir)}"

    if not target.is_dir():
        return f"Erreur : '{dir_path}' n'est pas un dossier, c'est un fichier. Utilise read_file_content pour le lire."

    return list_dir(target)
