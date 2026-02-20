import json
from pathlib import Path
from datetime import datetime
from tools._base import tool

CONTACTS_FILE = "contacts.json"


def _load_contacts(project_dir: Path) -> list[dict]:
    target = project_dir / CONTACTS_FILE
    if not target.exists():
        return []
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_contacts(project_dir: Path, contacts: list[dict]):
    target = project_dir / CONTACTS_FILE
    target.write_text(json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_id(contacts: list[dict]) -> int:
    if not contacts:
        return 1
    return max(c.get("id", 0) for c in contacts) + 1


def _match(contact: dict, query: str) -> bool:
    q = query.lower()
    for field in ("nom", "email", "telephone", "entreprise", "adresse", "notes"):
        val = contact.get(field, "")
        if val and q in str(val).lower():
            return True
    return False


@tool(
    name="manage_contacts",
    description=(
        "Gère le carnet de contacts du projet. "
        "Actions : 'add' (ajouter), 'search' (chercher par nom/email/entreprise), "
        "'update' (modifier), 'delete' (supprimer), 'list' (tout lister)."
    ),
    category="project",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "search", "update", "delete", "list"],
                "description": "L'action à effectuer.",
            },
            "nom": {
                "type": "string",
                "description": "Nom complet du contact (pour 'add' ou 'update').",
            },
            "telephone": {
                "type": "string",
                "description": "Numéro de téléphone (pour 'add' ou 'update').",
            },
            "email": {
                "type": "string",
                "description": "Adresse email (pour 'add' ou 'update').",
            },
            "adresse": {
                "type": "string",
                "description": "Adresse postale (pour 'add' ou 'update').",
            },
            "entreprise": {
                "type": "string",
                "description": "Nom de l'entreprise (pour 'add' ou 'update').",
            },
            "notes": {
                "type": "string",
                "description": "Notes libres sur le contact (pour 'add' ou 'update').",
            },
            "query": {
                "type": "string",
                "description": "Texte de recherche (pour 'search').",
            },
            "contact_id": {
                "type": "integer",
                "description": "ID du contact (pour 'update' ou 'delete').",
            },
        },
        "required": ["action"],
    },
)
def manage_contacts(args: dict, project_id: str, project_dir: Path) -> str:
    action = args.get("action", "")
    contacts = _load_contacts(project_dir)

    if action == "list":
        if not contacts:
            return "Aucun contact enregistré."
        return f"[AFFICHAGE_VISUEL] {len(contacts)} contact(s) affiché(s) dans le bloc interactif. Ne reproduis PAS la liste."

    if action == "search":
        query = args.get("query", "").strip()
        if not query:
            return "Erreur : 'query' est requis pour chercher un contact."
        results = [c for c in contacts if _match(c, query)]
        if not results:
            return f"Aucun contact trouvé pour « {query} »."
        lines = []
        for c in results:
            parts = [c.get("nom", "")]
            if c.get("telephone"):
                parts.append(c["telephone"])
            if c.get("email"):
                parts.append(c["email"])
            if c.get("entreprise"):
                parts.append(c["entreprise"])
            lines.append(f"#{c['id']} — " + " · ".join(parts))
        return f"{len(results)} contact(s) trouvé(s) :\n" + "\n".join(lines)

    if action == "add":
        nom = args.get("nom", "").strip()
        if not nom:
            return "Erreur : le nom du contact est requis."
        new_contact = {
            "id": _next_id(contacts),
            "nom": nom,
            "telephone": args.get("telephone", ""),
            "email": args.get("email", ""),
            "adresse": args.get("adresse", ""),
            "entreprise": args.get("entreprise", ""),
            "notes": args.get("notes", ""),
            "cree_le": datetime.now().strftime("%Y-%m-%d"),
        }
        contacts.append(new_contact)
        _save_contacts(project_dir, contacts)
        return f"Contact #{new_contact['id']} « {nom} » ajouté."

    if action == "update":
        contact_id = args.get("contact_id")
        if contact_id is None:
            return "Erreur : 'contact_id' est requis pour modifier un contact."
        target = next((c for c in contacts if c["id"] == contact_id), None)
        if not target:
            return f"Erreur : contact #{contact_id} introuvable."
        changed = []
        for field in ("nom", "telephone", "email", "adresse", "entreprise", "notes"):
            if field in args and args[field]:
                target[field] = args[field]
                changed.append(field)
        if not changed:
            return f"Aucune modification apportée au contact #{contact_id}."
        target["modifie_le"] = datetime.now().strftime("%Y-%m-%d")
        _save_contacts(project_dir, contacts)
        return f"Contact #{contact_id} mis à jour ({', '.join(changed)})."

    if action == "delete":
        contact_id = args.get("contact_id")
        if contact_id is None:
            return "Erreur : 'contact_id' est requis pour supprimer un contact."
        before = len(contacts)
        contacts = [c for c in contacts if c["id"] != contact_id]
        if len(contacts) == before:
            return f"Erreur : contact #{contact_id} introuvable."
        _save_contacts(project_dir, contacts)
        return f"Contact #{contact_id} supprimé."

    return f"Erreur : action '{action}' non reconnue."
