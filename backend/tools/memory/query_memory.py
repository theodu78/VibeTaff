from pathlib import Path
from tools._base import tool


@tool(
    name="query_project_memory",
    description="Recherche dans les documents indexés du projet (PDF, Excel, emails déposés par l'utilisateur). Renvoie les passages les plus pertinents. Utilise cet outil quand l'utilisateur pose une question sur le contenu de ses documents.",
    category="memory",
    requires_docs=True,
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "La question ou les mots-clés à rechercher dans les documents du projet.",
            },
            "top_k": {
                "type": "integer",
                "description": "Nombre de passages à renvoyer (défaut: 5, max: 10).",
            },
        },
        "required": ["question"],
    },
)
def query_project_memory(args: dict, project_id: str, project_dir: Path) -> str:
    from ingestion.embedder import embed_single
    from ingestion.store import search_chunks

    question = args.get("question", "")
    if not question:
        return "Erreur : Aucune question fournie."

    top_k = min(args.get("top_k", 5), 10)
    query_vector = embed_single(question)
    results = search_chunks(project_id, query_vector, top_k=top_k)

    if not results:
        return "Aucun document n'a été trouvé dans le projet. L'utilisateur doit d'abord déposer des fichiers (PDF, Excel, etc.) dans l'application."

    parts = []
    for i, r in enumerate(results, 1):
        source = r.get("source_file", "inconnu")
        text = r.get("text", "")
        parts.append(f"--- Passage {i} (source: {source}) ---\n{text}")

    return "\n\n".join(parts)
