import os
from pathlib import Path
from tools._base import tool


@tool(
    name="web_search",
    description=(
        "Recherche sur le web. Renvoie un résumé structuré et les sources. "
        "QUAND l'utiliser : pour des infos en temps réel (cours, taux de change, actualités, "
        "lois récentes, prix du marché). "
        "QUAND NE PAS l'utiliser : pour des infos qui sont déjà dans les documents du projet — "
        "utilise query_project_memory. "
        "LIMITE : max 2 recherches par message. Formule des requêtes précises et spécifiques."
    ),
    category="web",
    requires_env=["TAVILY_API_KEY"],
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "La requête de recherche web (ex: 'cours EUR/USD aujourd'hui', 'PIB France 2025').",
            },
        },
        "required": ["query"],
    },
)
def web_search(args: dict, project_id: str, project_dir: Path) -> str:
    query = args.get("query", "").strip()
    if not query:
        return "Erreur : Aucune requête de recherche fournie."

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Erreur : La clé API Tavily n'est pas configurée."

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=5, include_answer=True)

        parts = []
        answer = response.get("answer")
        if answer:
            parts.append(f"Résumé : {answer}")

        results = response.get("results", [])
        if results:
            parts.append("\nSources :")
            for i, r in enumerate(results, 1):
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = r.get("content", "")[:200]
                parts.append(f"{i}. {title}\n   {url}\n   {snippet}")

        return "\n".join(parts) if parts else "Aucun résultat trouvé."

    except Exception as e:
        return f"Erreur lors de la recherche web : {str(e)}"
