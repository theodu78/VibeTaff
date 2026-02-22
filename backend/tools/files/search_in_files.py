import re
from pathlib import Path
from tools._base import tool, resolve_safe_path

MAX_RESULTS = 30
MAX_LINE_LEN = 200
SKIP_DIRS = {".git", "__pycache__", "node_modules", "_config", ".vibetaff"}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".csv", ".json", ".py", ".js", ".ts", ".tsx",
    ".html", ".css", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".log", ".sh", ".bat", ".sql", ".env", ".eml",
}


@tool(
    name="search_in_files",
    description=(
        "Recherche un texte exact ou un pattern regex dans les fichiers texte du projet. "
        "Retourne les lignes correspondantes avec le nom du fichier et le numéro de ligne. "
        "QUAND l'utiliser : quand tu connais le mot ou l'expression EXACTE à chercher "
        "(nom propre, montant, référence, numéro de facture). "
        "QUAND NE PAS l'utiliser : pour des questions sémantiques ou vagues — "
        "utilise query_project_memory (recherche par sens, pas par mot exact). "
        "LIMITE : max 30 résultats retournés."
    ),
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Le texte ou pattern regex à rechercher.",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Respecter la casse (défaut: false).",
            },
        },
        "required": ["query"],
    },
)
def search_in_files(args: dict, project_id: str, project_dir: Path) -> str:
    query = args.get("query", "").strip()
    if not query:
        return "Erreur : aucun texte de recherche fourni."

    case_sensitive = args.get("case_sensitive", False)
    flags = 0 if case_sensitive else re.IGNORECASE

    try:
        pattern = re.compile(query, flags)
    except re.error:
        pattern = re.compile(re.escape(query), flags)

    matches = []

    for path in project_dir.rglob("*"):
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_num, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                rel = path.relative_to(project_dir)
                display_line = line.strip()
                if len(display_line) > MAX_LINE_LEN:
                    display_line = display_line[:MAX_LINE_LEN] + "..."
                matches.append(f"{rel}:{line_num}: {display_line}")
                if len(matches) >= MAX_RESULTS:
                    break
        if len(matches) >= MAX_RESULTS:
            break

    if not matches:
        return f"Aucun résultat pour '{query}' dans les fichiers du projet."

    header = f"{len(matches)} résultat(s) pour '{query}' :"
    if len(matches) >= MAX_RESULTS:
        header += f" (limité à {MAX_RESULTS}, il peut y en avoir plus)"
    return header + "\n" + "\n".join(matches)
