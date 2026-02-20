import json
from pathlib import Path
from tools._base import tool, resolve_safe_path


@tool(
    name="write_json_table",
    description="Crée un fichier JSON contenant un tableau de données structuré. Utilisé pour sauvegarder des tableaux, listes et données tabulaires.",
    category="files",
    parameters={
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
)
def write_json_table(args: dict, project_id: str, project_dir: Path) -> str:
    table_name = args.get("table_name", "")
    json_data = args.get("json_data", [])

    if not table_name:
        return "Erreur : Le nom du tableau est vide."

    safe_name = "".join(c for c in table_name if c.isalnum() or c in "-_ ").strip()
    if not safe_name:
        return "Erreur : Le nom ne contient aucun caractère valide."

    file_name = f"{safe_name}.json"
    target = resolve_safe_path(project_dir, file_name)
    if target is None:
        return f"Erreur : Le nom '{file_name}' n'est pas valide."

    target.write_text(
        json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    row_count = len(json_data) if isinstance(json_data, list) else 0
    return f"Le tableau '{file_name}' a été créé avec succès ({row_count} lignes)."
