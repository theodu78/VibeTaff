⚠️ Pre-Mortem & Risques Techniques (Vibetaff V1)

Document de Guidage Architectural pour l'Ingénierie
Dernière mise à jour : 20 février 2026 (arbitrages finalisés)

Ce document identifie les 5 murs techniques majeurs du projet et impose l'architecture exacte pour les contourner. L'objectif est d'éviter les "hacks" et de forcer l'utilisation des standards industriels dès la V1.
1. Le Goulot d'Étranglement : La Communication Tauri ↔ Python

    Le Piège : Utiliser des requêtes HTTP REST classiques (GET/POST) entre le front-end et le back-end. Le LLM (DeepSeek) prend du temps à générer sa réponse. Une requête HTTP classique va faire un Timeout (geler), et il sera impossible d'afficher le texte lettre par lettre (streaming) ou de faire apparaître des interfaces dynamiques (Generative UI) en temps réel.

    La Solution Imposée (Le Standard) : Le protocole Server-Sent Events (SSE) au format "UI Message Stream Protocol" du Vercel AI SDK.

        Backend (FastAPI) : Utiliser exclusivement StreamingResponse. Le backend "pousse" des événements SSE JSON typés dans le flux. Header obligatoire : x-vercel-ai-ui-message-stream: v1.

        Format SSE exact (vérifié en veille technique, ~15 types d'événements) :
            Texte :       {"type":"start","messageId":"..."} → {"type":"text-delta","id":"...","delta":"Bonjour"} → {"type":"text-end","id":"..."} → {"type":"finish"}
            Tool calls :  {"type":"tool-input-start","toolCallId":"...","toolName":"..."} → {"type":"tool-input-delta",...} → {"type":"tool-input-available","input":{...}} → {"type":"tool-output-available","output":{...}}
            Custom data : {"type":"data-datagrid","data":{...}} (pour les composants Generative UI custom)
            Steps :       {"type":"start-step"} / {"type":"finish-step"} (séparateurs entre les itérations de la boucle agentique)
            Fin :         data: [DONE]

        Frontend (React/Tauri) : Ne pas coder de parser manuel. Utiliser le hook useChat du Vercel AI SDK (@ai-sdk/react), qui consomme nativement ce protocole SSE. Les tool parts sont typées (case "tool-nomDeLoutil") et rendues automatiquement en composants React.

2. Le Blocage du Serveur : Le "Human-in-the-Loop"

    Le Piège : Lorsqu'un outil critique est appelé (ex: draft_email), l'Agent doit être mis en pause pour attendre le clic d'approbation de l'utilisateur. Si cette pause est codée avec un simple time.sleep() ou une boucle while, elle va bloquer le thread principal (Event Loop) de FastAPI. L'application entière va crasher.

    La Solution Initiale (asyncio.Event + UUID) : Abandonnée après veille technique.
    L'idée de garder un flux SSE ouvert en attente, avec un asyncio.Event côté backend, marchait en théorie mais ajoutait une complexité inutile (gestion d'UUID, endpoint /api/approve_action, risque de leak de connexions).

    La Solution Finale (Veille technique — 20 fév 2026) : Le Vercel AI SDK gère ça nativement via un pattern multi-requêtes.

        Le mécanisme s'appuie sur 2 concepts natifs du SDK :
        1. Client-side tools (outils sans fonction execute côté serveur) : Le backend stream les données de l'outil (tool-input-available), puis FERME le flux SSE. Le frontend affiche le composant interactif (email, QCM). Quand l'utilisateur valide, le SDK appelle addToolOutput() et RELANCE automatiquement une nouvelle requête HTTP vers /api/chat avec l'historique complet + le résultat de l'outil. Le backend reprend la boucle agentique sur cette nouvelle requête.
        2. Tool Execution Approval (needsApproval: true) : Pour les outils exécutés côté serveur mais dangereux (ex: écraser un fichier), le SDK met l'outil en état "approval-requested". L'utilisateur voit un bouton Approuver/Refuser. Le clic appelle addToolApprovalResponse() → nouvelle requête → le backend exécute l'outil.

        Conséquence architecturale : La "boucle agentique" n'est pas une seule longue requête HTTP. C'est une série de requêtes courtes. Le frontend gère le cycle via sendAutomaticallyWhen (auto-relance quand tous les résultats d'outils sont disponibles). Le backend reste stateless entre les requêtes — pas d'asyncio.Event, pas d'UUID, pas de connexions ouvertes.

        Avantage : Plus simple, plus robuste, pas de risque de fuite mémoire ou de thread bloqué. Le SDK est testé en production sur des millions d'utilisateurs (Vercel).

3. La "Fatigue Cognitive" du LLM : Le RAG Tabulaire

    Le Piège : Ingestion aveugle de fichiers Excel ou PDF complexes. Si on découpe (chunk) un tableau Markdown de 500 lignes tous les 1000 caractères, le LLM va recevoir des morceaux de tableau sans les en-têtes de colonnes. Le contexte va saturer et l'Agent va halluciner les chiffres.

    La Solution Imposée : 1. Chunking Sémantique : Le script d'ingestion (Python) doit obligatoirement répéter les en-têtes de tableau (ex: | Produit | Prix |) au début de chaque "chunk" inséré dans LanceDB.
    2. Délégation CPU (Map-Reduce) : Pour faire la somme d'un devis entier, l'Agent ne doit pas essayer de lire tout le fichier dans son contexte LLM. L'Agent doit utiliser son outil run_local_calculation pour pondre un script Python qui lit le CSV physiquement sur le disque et lui renvoie uniquement le résultat mathématique.

4. Le Syndrome de l'Agent Fou : La Boucle Infinie

    Le Piège : L'Agent appelle un outil avec un mauvais paramètre (ex: fichier introuvable). L'outil renvoie une erreur brute (HTTP 404 ou File Not Found). L'Agent panique et tente de rappeler le même outil en boucle jusqu'à exploser le quota de l'API DeepSeek.

    La Solution Imposée :

        Circuit Breaker : Le backend doit imposer une limite stricte (max_steps = 5 par exemple) dans la boucle Agentique.

        Gestion d'Erreurs Verbeuse (Feedback Loop) : Les outils (Tools) ne doivent jamais "crasher". S'il y a une erreur système, l'outil doit faire un return d'un texte explicatif formaté pour le LLM.

            Exemple : return "Erreur : Le fichier 'devis.md' n'existe pas. Voici les fichiers présents dans le répertoire : ['devis_v2.md', 'plan.md']. Corrige ton appel."

5. La Faille de Sécurité : La Sandbox WASM dans Python

    Le Piège : Pour exécuter le code Python généré par l'outil run_local_calculation, l'IA de vibecoding va proposer la solution de facilité : utiliser les fonctions natives Python exec() ou eval(). C'est une faille critique qui détruit le "Workspace Jail" et donne à l'Agent un accès administrateur à la machine hôte.

    La Solution Imposée : L'exécution de code généré par le LLM se fait exclusivement via une librairie de Sandboxing (WASM).

        Imposer l'utilisation de wasmtime-py ou d'un wrapper Pyodide local.

        Le code "Hôte" (FastAPI) et le code "Invité" (WASM) ne communiquent que par des chaînes de caractères (String In / String Out). Aucun accès au système de fichiers ou au réseau n'est injecté dans la machine WASM par défaut.

6. Registre des Arbitrages Techniques (Février 2026)

Décisions prises lors de la phase de conception, avec justification :

    LanceDB (Apache 2.0) retenu, Khoj (AGPL-3.0) écarté.
    Khoj est un produit complet concurrent (assistant IA avec sa propre UI), pas une brique composable. Sa licence AGPL imposerait l'open-sourcing de tout VibeTaff. LanceDB est une simple librairie embarquée qu'on intègre dans notre pipeline maison.

    Pipeline d'ingestion maison (~300 lignes Python) plutôt que fork d'un projet existant.
    PyMuPDF4LLM (PDF) + pandas/openpyxl (Excel) + BeautifulSoup (emails) + sentence-transformers (embeddings) + LanceDB (stockage). Avantage : contrôle total sur le chunking sémantique (répétition des en-têtes tabulaires, cf. §3).

    Tavily retenu comme API de recherche web.
    API optimisée pour les agents IA (résultats pré-structurés). Standard de l'écosystème OpenClaw. Tier gratuit : 1 000 req/mois.

    Emails V1 : brouillon + mailto: (pas d'OAuth/SMTP).
    L'Agent génère un brouillon visuel dans le chat. Le bouton [Envoyer] ouvre le client mail natif (Apple Mail, Outlook…) via lien mailto: pré-rempli. Intégration OAuth Gmail/Outlook repoussée en V2.

    PyInstaller pour le packaging du sidecar Python.
    Le backend FastAPI est compilé en exécutable autonome (~50-80 Mo). L'utilisateur final n'a pas besoin d'installer Python. L'exécutable est placé dans src-tauri/binaries/ et lancé automatiquement par Tauri.

    Plateforme V1 : macOS uniquement.
    Simplifie le développement et le testing. Windows/Linux envisagés en V2.