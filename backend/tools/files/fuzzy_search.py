from pathlib import Path
from tools._base import tool

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_config", ".vibetaff"}
MAX_RESULTS = 15


def _fuzzy_score(query: str, name: str) -> float:
    """Simple fuzzy scoring: how well does query match name (0.0 to 1.0)."""
    query_lower = query.lower()
    name_lower = name.lower()

    if query_lower == name_lower:
        return 1.0
    if query_lower in name_lower:
        return 0.8 + 0.2 * (len(query_lower) / len(name_lower))

    qi = 0
    matches = 0
    for char in name_lower:
        if qi < len(query_lower) and char == query_lower[qi]:
            matches += 1
            qi += 1

    if qi < len(query_lower):
        return 0.0

    return 0.5 * (matches / len(name_lower)) + 0.5 * (matches / max(len(query_lower), 1))


@tool(
    name="fuzzy_file_search",
    description=(
        "Recherche floue de fichiers par nom dans le projet. "
        "Trouve les fichiers même si le nom est approximatif ou partiel. "
        "QUAND l'utiliser : quand l'utilisateur mentionne un fichier par un nom approximatif "
        "(ex: 'le devis omega', 'le rapport carbone') ou quand tu veux localiser un fichier. "
        "QUAND NE PAS l'utiliser : pour lister TOUS les fichiers (utilise list_project_files), "
        "pour chercher du contenu DANS les fichiers (utilise search_in_files ou query_project_memory)."
    ),
    category="files",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Le nom (même partiel ou approximatif) du fichier à chercher.",
            },
        },
        "required": ["query"],
    },
)
def fuzzy_file_search(args: dict, project_id: str, project_dir: Path) -> str:
    query = args.get("query", "").strip()
    if not query:
        return "Erreur : aucun terme de recherche fourni."

    scored: list[tuple[float, str]] = []

    for path in project_dir.rglob("*"):
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if not path.is_file():
            continue

        rel = str(path.relative_to(project_dir))
        name_score = _fuzzy_score(query, path.stem)
        path_score = _fuzzy_score(query, rel)
        score = max(name_score, path_score)

        if score > 0.1:
            scored.append((score, rel))

    if not scored:
        return f"Aucun fichier correspondant à '{query}'."

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:MAX_RESULTS]

    lines = [f"{rel}  (score: {score:.0%})" for score, rel in top]
    return f"{len(top)} fichier(s) trouvé(s) pour '{query}' :\n" + "\n".join(lines)
