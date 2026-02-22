import subprocess
import sys
from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="open_file_on_desktop",
    description=(
        "Ouvre un fichier avec l'application par défaut du système (Aperçu pour PDF, Excel pour .xlsx). "
        "QUAND l'utiliser : quand l'utilisateur dit 'ouvre le fichier', 'montre-moi le PDF', "
        "'affiche le document'. "
        "QUAND NE PAS l'utiliser : pour lire le CONTENU d'un fichier dans le chat — "
        "utilise read_file_content à la place."
    ),
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "file_name": {
                "type": "string",
                "description": "Chemin relatif du fichier à ouvrir (ex: '_uploads/rapport.pdf')",
            }
        },
        "required": ["file_name"],
    },
)
def open_file_on_desktop(args: dict, project_id: str, project_dir: Path) -> str:
    file_name = args.get("file_name", "")
    if not file_name:
        return "Erreur : Aucun nom de fichier fourni."

    target = resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le chemin '{file_name}' sort du périmètre du projet."

    if not target.exists():
        import unicodedata
        name_nfc = unicodedata.normalize("NFC", Path(file_name).name)
        for p in project_dir.rglob("*"):
            if p.is_file() and unicodedata.normalize("NFC", p.name) == name_nfc:
                target = p
                break
        else:
            return f"Erreur : Le fichier '{file_name}' n'existe pas."

    if sys.platform != "darwin":
        return f"Erreur : L'ouverture de fichiers n'est supportée que sur macOS."

    try:
        subprocess.Popen(["open", str(target)])
        return f"Le fichier '{target.name}' a été ouvert avec l'application par défaut."
    except Exception as e:
        return f"Erreur lors de l'ouverture : {e}"
