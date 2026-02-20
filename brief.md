🚀 Vibetaff : Le "Cursor" des Travailleurs du Savoir

Document d'Architecture Globale & Spécifications (V1 - Février 2026)
1. La Vision & Le Concept

L'objectif est de créer le "Cursor du taff administratif et analytique" : un Agent OS local, capable de raisonner, de chercher et d'agir de manière autonome sur des dossiers complexes (Contrats, Bilans financiers, Factures, E-mails).

    Le Problème : Les professionnels perdent un temps infini à croiser des informations enfermées dans des "silos visuels" (Excel, PDF, E-mails). Les LLM classiques (ChatGPT) n'ont pas accès à ces fichiers locaux ou les comprennent mal.

    La Solution ("Vibetaff") : Un logiciel de bureau léger où l'utilisateur pilote un Agent IA par intention. L'Agent ingère les documents crades, les traduit en données structurées, s'adapte aux bases de références de l'utilisateur, et génère le livrable final via une interface générative.

2. Architecture Technique (La Stack "Sidecar")

L'application hybride allie la vitesse d'une interface locale et l'intelligence d'une API Cloud puissante.
Plateforme cible V1 : macOS uniquement. (Windows/Linux envisagés en V2.)

    Frontend (L'Interface visuelle) : Tauri v2 + React/Tailwind
    Poids plume (~10 Mo), utilise le moteur web natif de l'OS (WebKit sur macOS).
    Le streaming LLM et la Generative UI sont gérés via le hook useChat du Vercel AI SDK (@ai-sdk/react).
    Note veille technique : Le SDK utilise le "UI Message Stream Protocol" (SSE). Le backend doit envoyer des événements JSON typés (text-delta, tool-input-available, tool-output-available, data-*, finish, etc.) et positionner le header x-vercel-ai-ui-message-stream: v1. Ce n'est pas du texte brut — c'est un protocole structuré d'environ 15 types d'événements SSE documentés.

    Backend (Le Moteur Local) : Python (via FastAPI en Sidecar)
    Tourne silencieusement en tâche de fond pour gérer les fichiers et la sécurité.
    Distribution : le code Python est compilé en exécutable autonome via PyInstaller (--onefile). L'utilisateur final n'a pas besoin d'installer Python. L'exécutable est embarqué dans le bundle Tauri comme sidecar (src-tauri/binaries/).

    Le Cerveau (Cloud LLM) : API DeepSeek V3
    Le moteur de raisonnement. Choisi pour son ratio coût/intelligence imbattable et sa compatibilité parfaite avec le format de Tool Calling d'OpenAI.
    Note veille technique : Le modèle s'appelle "deepseek-chat" dans l'API (correspond à DeepSeek-V3.2, 128K de contexte). Endpoint : https://api.deepseek.com/chat/completions. On utilise le SDK Python openai avec base_url="https://api.deepseek.com". Le Tool Calling supporte un mode "strict" (beta) qui force le respect du JSON Schema — à activer pour fiabiliser les appels d'outils.

    La Mémoire Documentaire (RAG) : LanceDB
    Base vectorielle locale embarquée (pas de serveur à lancer) pour indexer les PDF/Excel du projet.
    Arbitrage : Khoj (AGPL-3.0) a été écarté — c'est un produit complet concurrent, pas une brique composable. Sa licence copyleft est incompatible avec une distribution propriétaire future. LanceDB (Apache 2.0) est une simple librairie légère qu'on intègre dans notre pipeline.

    Le Moteur d'Embeddings : sentence-transformers (local)
    Modèle local (all-MiniLM-L6-v2 ou équivalent) pour transformer le texte en vecteurs. Gratuit, rapide, pas d'appel API. Les embeddings sont générés côté backend Python avant insertion dans LanceDB.

    La Recherche Web : API Tavily
    API de recherche optimisée pour les agents IA. Retourne des résultats pré-structurés et résumés, directement exploitables par le LLM. Tier gratuit : 1 000 requêtes/mois. Standard utilisé par l'écosystème OpenClaw.

    La Mémoire d'État & Historique : SQLite
    Base de données locale classique pour sauvegarder l'historique des chats et la mémoire à long terme de l'Agent.

3. Le Pipeline d'Ingestion : "Sanitizer" la donnée

Note Scope V1 : Le système est purement textuel/tabulaire. Les images et plans ne sont pas analysés par l'IA dans cette version.

Le pipeline maison (~300 lignes Python) suit 4 étapes systématiques : Extraction → Chunking → Embedding → Stockage.

A. Étape 1 — Extraction (Fichier → Markdown brut)

    PDF / Word : PyMuPDF4LLM écrase la mise en forme et extrait les tableaux en Markdown pur.
    Excel / CSV : pandas + openpyxl convertissent les feuilles en tableaux Markdown (| Col A | Col B |).
    E-mails (.eml, .msg) : BeautifulSoup supprime le HTML et les signatures. Le mail devient un fichier texte structuré (De, À, Date, Sujet, Corps). Les pièces jointes utiles sont sauvegardées dans le dossier local du projet et réinjectées dans le pipeline.

B. Étape 2 — Chunking Sémantique (Markdown → Morceaux intelligents)

    Le Markdown brut est découpé en chunks de ~800 tokens.
    Règle critique (cf. Premortem §3) : les en-têtes de tableau (ex: | Produit | Prix |) sont répétés au début de chaque chunk pour que le LLM ne perde jamais le contexte des colonnes.
    Les métadonnées du fichier source (nom, type, date) sont attachées à chaque chunk.

C. Étape 3 — Embedding (Morceaux → Vecteurs)

    Chaque chunk est transformé en vecteur par le modèle local sentence-transformers (all-MiniLM-L6-v2).
    Aucun appel API externe : tout est calculé localement, gratuitement.

D. Étape 4 — Stockage (Vecteurs → LanceDB)

    Les vecteurs + le texte original + les métadonnées sont insérés dans LanceDB.
    L'Agent peut ensuite interroger cette base via l'outil query_project_memory(question) pour retrouver l'info pertinente par recherche sémantique.

4. 🌟 La Boîte à Outils de l'Agent (Les "Skills")

L'Agent (piloté par DeepSeek V3) manipule l'environnement via le standard MCP / Tool Calling.
📁 Opérations Fichiers (Restreint au "Workspace Jail")

    list_project_files(directory_path) : Voit ce qu'il y a dans le dossier du projet.

    read_file_content(file_name) : Lit le contenu Markdown d'un document.

    write_project_note(title, markdown_content) : Crée un document texte (brouillon ou rapport).

    write_json_table(table_name, json_data) : Crée un tableau de données structuré.

🧮 Analyse, Logique & Mémoire

    run_local_calculation(python_code) : (Le super-pouvoir) L'Agent génère et exécute un script Python dans une sandbox (WASM) pour faire des calculs complexes ou parser un fichier de référence client (Bring Your Own Data).

    query_project_memory(question) : Interroge LanceDB pour retrouver une info précise dans un PDF de 500 pages.

    save_to_long_term_memory(key, value) : Écrit dans SQLite pour mémoriser les préférences de l'utilisateur (ex: "Le client Alpha préfère les marges à 20%").

🌐 Communication Extérieure

    web_search(query) : Interroge l'API Tavily (recherche optimisée IA) pour chercher des lois, des prix du marché ou de l'actu. Retourne un résumé structuré + sources.

    draft_email(to, subject, body) : Prépare un brouillon d'e-mail affiché dans un composant interactif dans le chat. Scope V1 : le bouton [Envoyer] ouvre le client mail par défaut de l'utilisateur (Apple Mail, Outlook…) via un lien mailto: pré-rempli. Pas d'intégration OAuth/SMTP en V1 (prévu V2).

5. Architecture UX : La "Generative UI"

Le chat est une toile dynamique. Lorsqu'un "Tool" est appelé, l'interface React affiche des composants interactifs.

Note veille technique — Mécanisme interne du Vercel AI SDK :
Le SDK distingue 3 catégories d'outils qui déterminent le rendu dans le chat :
    - Server-side tools (avec execute côté backend) : exécutés automatiquement, résultat streamé. Utilisés pour : list_project_files, read_file_content, query_project_memory, web_search, run_local_calculation.
    - Client-side tools (sans execute, attendent l'utilisateur) : le SDK affiche le composant React associé et attend que l'utilisateur interagisse via addToolOutput(). Utilisés pour : draft_email (brouillon éditable), ask_human (QCM).
    - Tools with needsApproval : exécutés côté serveur MAIS seulement après validation via addToolApprovalResponse(). Utilisés pour : write_project_note (écraser un fichier existant).
Le SDK utilise aussi les "custom data parts" (type: "data-*") pour envoyer des données structurées arbitraires dans le flux SSE. On les utilise pour les DataGrids et les LiveDiffs.

Composants Generative UI :

    Le QCM (Ask Human) : Client-side tool. Si un contrat est ambigu, l'Agent affiche des boutons radio dans le chat pour demander une clarification. La réponse est renvoyée au backend via addToolOutput() et la boucle agentique reprend automatiquement.

    Le Tableau Interactif (Data Grid) : Envoyé comme custom data part (type: "data-datagrid"). L'Agent génère un tableau propre (triable et modifiable par l'humain) directement dans la conversation. (Scope V1 : Export via simple bouton "Copier CSV", pas de remplissage de templates Excel complexes).

    Vue Live Diff : Envoyée comme custom data part (type: "data-diff"). Si l'Agent modifie une note existante, l'utilisateur voit les lignes supprimées (rouge) et ajoutées (vert) s'afficher en streaming.

    Le Brouillon d'E-mail : Client-side tool. L'outil génère un composant avec des champs éditables (destinataire, objet, corps) et un bouton [Envoyer]. L'utilisateur modifie le brouillon puis valide via addToolOutput(). En V1, le bouton [Envoyer] ouvre le client mail natif (Apple Mail, Outlook…) via mailto: pré-rempli. Intégration OAuth directe prévue en V2.

6. Architecture de Sécurité (Zero Trust)

L'Agent est confiné pour protéger le PC de l'utilisateur.

    L'Environnement Isolée (WASM / Pyodide) : Quand l'outil run_local_calculation exécute du code Python, il tourne dans un bac à sable sans accès au disque dur principal ni au réseau.

    Le Périmètre Strict (Workspace Jail) : Le backend Python bloque toute requête essayant de sortir du dossier du projet en cours (ex: C:/Vibetaff/Projets/Dossier_Client_A/).

    Human-In-The-Loop : L'Agent lit et réfléchit seul. Mais pour toute action sortante (envoyer un mail, écraser un fichier), l'interface Tauri exige un clic de validation explicite. Aucun accès au terminal (bash, cmd) n'est fourni.

7. Le Workflow Utilisateur Type (Le "Aha Moment")

    Création : Un consultant financier crée le projet "Audit Omega".

    Alimentation : Il glisse 3 bilans PDF, 1 export Excel brut et 2 e-mails vitaux dans l'application.

    Intention : Il tape : "Compare l'EBITDA des 3 dernières années, vérifie les taux de change actuels sur le web, et dresse un tableau de synthèse. Mémorise que je veux les montants en k€. Prépare aussi un mail pour le DAF."

    Exécution Agentique : L'Agent interroge la mémoire, scappe le web, écrit un script Python à la volée pour nettoyer l'export Excel (BYOD), génère un Data Grid dans le chat, et affiche un brouillon d'e-mail.

    Validation : Le consultant valide le tableau, le copie en CSV, et clique sur [Envoyer] pour le mail. S'il ferme l'app, l'historique complet est sauvegardé dans SQLite.