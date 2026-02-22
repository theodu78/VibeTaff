from pathlib import Path
from tools._base import tool


@tool(
    name="query_project_memory",
    description=(
        "Recherche sémantique dans tous les documents indexés du projet (PDF, Excel, emails). "
        "C'est l'outil PRINCIPAL pour trouver une information dans les documents. "
        "QUAND l'utiliser : en PREMIER quand l'utilisateur pose une question sur ses documents. "
        "QUAND NE PAS l'utiliser : pour lister les fichiers (utilise list_project_files), "
        "pour lire un fichier spécifique déjà connu (utilise read_file_content). "
        "STRATÉGIE : pose des questions en langage naturel. Pour analyser PLUSIEURS documents, "
        "fais 2-3 requêtes thématiques ('finances', 'contacts', 'technique') plutôt que de "
        "lire chaque fichier individuellement."
    ),
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
