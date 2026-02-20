from pathlib import Path
from datetime import datetime
from tools._base import tool, resolve_safe_path


@tool(
    name="save_meeting_note",
    description=(
        "Crée un compte-rendu de réunion structuré en Markdown dans le dossier 'reunions/' du projet. "
        "Génère automatiquement un nom de fichier avec la date du jour."
    ),
    category="project",
    requires_approval=True,
    parameters={
        "type": "object",
        "properties": {
            "titre": {
                "type": "string",
                "description": "Titre court de la réunion (ex: 'point-chantier-A', 'revue-budget'). Sera inclus dans le nom du fichier.",
            },
            "participants": {
                "type": "string",
                "description": "Liste des participants séparés par des virgules (ex: 'Jean, Marie, Paul').",
            },
            "duree": {
                "type": "string",
                "description": "Durée de la réunion (ex: '45 min', '1h30'). Optionnel.",
            },
            "points_abordes": {
                "type": "string",
                "description": "Les sujets discutés, en texte libre ou liste à puces Markdown.",
            },
            "actions": {
                "type": "string",
                "description": "Les actions décidées avec responsable et deadline si connu. Format Markdown (listes à puces ou checklist).",
            },
            "notes_complementaires": {
                "type": "string",
                "description": "Informations complémentaires, contexte, décisions importantes. Optionnel.",
            },
            "date": {
                "type": "string",
                "description": "Date de la réunion au format YYYY-MM-DD. Si non fourni, utilise la date du jour.",
            },
        },
        "required": ["titre", "points_abordes"],
    },
)
def save_meeting_note(args: dict, project_id: str, project_dir: Path) -> str:
    titre = args.get("titre", "").strip()
    if not titre:
        return "Erreur : le titre de la réunion est vide."

    date_str = args.get("date", datetime.now().strftime("%Y-%m-%d"))
    participants = args.get("participants", "")
    duree = args.get("duree", "")
    points = args.get("points_abordes", "")
    actions = args.get("actions", "")
    notes = args.get("notes_complementaires", "")

    safe_titre = "".join(c for c in titre if c.isalnum() or c in "-_ ").strip().replace(" ", "-").lower()
    if not safe_titre:
        return "Erreur : le titre ne contient aucun caractère valide."

    reunions_dir = project_dir / "reunions"
    reunions_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{date_str}-{safe_titre}.md"
    target = resolve_safe_path(reunions_dir, file_name)
    if target is None:
        return f"Erreur : nom de fichier '{file_name}' invalide."

    lines = [f"# {titre.replace('-', ' ').title()} — {date_str}", ""]

    meta = []
    if participants:
        meta.append(f"**Participants** : {participants}")
    if duree:
        meta.append(f"**Durée** : {duree}")
    if meta:
        lines.extend(meta)
        lines.append("")

    lines.append("## Points abordés")
    lines.append("")
    lines.append(points)
    lines.append("")

    if actions:
        lines.append("## Actions")
        lines.append("")
        lines.append(actions)
        lines.append("")

    if notes:
        lines.append("## Notes complémentaires")
        lines.append("")
        lines.append(notes)
        lines.append("")

    content = "\n".join(lines)
    target.write_text(content, encoding="utf-8")

    return f"Compte-rendu '{file_name}' créé dans le dossier 'reunions/' ({len(content)} caractères)."
