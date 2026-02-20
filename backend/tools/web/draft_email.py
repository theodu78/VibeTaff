import json
import urllib.parse
from pathlib import Path
from tools._base import tool


@tool(
    name="draft_email",
    description="Prépare un brouillon d'email. N'envoie rien : le brouillon est affiché dans le chat pour validation par l'utilisateur, qui pourra l'envoyer via son client mail.",
    category="web",
    requires_approval=True,
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Adresse email du destinataire.",
            },
            "subject": {
                "type": "string",
                "description": "Objet de l'email.",
            },
            "body": {
                "type": "string",
                "description": "Corps de l'email en texte brut.",
            },
        },
        "required": ["to", "subject", "body"],
    },
)
def draft_email(args: dict, project_id: str, project_dir: Path) -> str:
    to = args.get("to", "").strip()
    subject = args.get("subject", "").strip()
    body = args.get("body", "").strip()

    if not to:
        return "Erreur : Le destinataire est vide."
    if not subject:
        return "Erreur : L'objet de l'email est vide."
    if not body:
        return "Erreur : Le corps de l'email est vide."

    mailto = (
        f"mailto:{urllib.parse.quote(to)}"
        f"?subject={urllib.parse.quote(subject)}"
        f"&body={urllib.parse.quote(body)}"
    )

    return json.dumps({
        "type": "email_draft",
        "to": to,
        "subject": subject,
        "body": body,
        "mailto_link": mailto,
    }, ensure_ascii=False)
