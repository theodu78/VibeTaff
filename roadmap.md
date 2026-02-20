🗺️ Roadmap Vibetaff V1 — De Zéro au .dmg

Dernière mise à jour : 20 février 2026
Documents de référence : brief.md (spécifications) · premortem.md (risques & arbitrages)

Le développement est découpé en 9 phases séquentielles. Chaque phase produit un livrable testable.
Les dépendances sont indiquées : aucune phase ne peut démarrer si la précédente n'est pas "Done".

────────────────────────────────────────────────────────────────

PHASE 0 — Les Fondations (Scaffolding)

    Objectif : L'app s'ouvre sur Mac, le front React parle au back Python.

    Tâches :
    0.1  Initialiser le projet Tauri v2 avec le template React + TypeScript.
    0.2  Installer Tailwind CSS dans le frontend.
    0.3  Créer le projet Python (FastAPI) dans un dossier backend/.
    0.4  Configurer Tauri pour lancer FastAPI en sidecar (externalBin dans tauri.conf.json).
    0.5  Créer un endpoint de santé GET /api/health → { "status": "ok" }.
    0.6  Au démarrage de l'app Tauri, lancer le sidecar et vérifier la connexion (ping /health).
    0.7  Afficher "Connecté au backend" dans l'interface React quand le ping réussit.

    Livrables :
    - Structure de dossiers propre (src/ pour React, backend/ pour Python, src-tauri/ pour Rust).
    - L'app Tauri s'ouvre, affiche une page blanche avec le statut du backend.

    Definition of Done : npm run tauri dev lance l'app + le sidecar. Le front affiche "Connecté".

────────────────────────────────────────────────────────────────

PHASE 1 — Le Chat en Streaming

    Objectif : L'utilisateur tape un message, DeepSeek répond en streaming lettre par lettre.

    Dépendance : Phase 0 terminée.

    Tâches :
    1.1  Backend : Créer POST /api/chat qui reçoit l'historique des messages (format UIMessage du Vercel AI SDK).
    1.2  Backend : Appeler l'API DeepSeek V3 en streaming (model="deepseek-chat", stream=True, via SDK openai avec base_url="https://api.deepseek.com").
    1.3  Backend : Retourner la réponse via StreamingResponse (SSE) au format "UI Message Stream Protocol" :
         - Header obligatoire : x-vercel-ai-ui-message-stream: v1
         - Événements : start → text-start → text-delta (par chunk) → text-end → finish → [DONE]
         ⚠️ Premortem §1 : pas de REST classique, SSE obligatoire. Format précis imposé par le SDK.
    1.4  Frontend : Installer le Vercel AI SDK (ai + @ai-sdk/react).
    1.5  Frontend : Utiliser le hook useChat avec DefaultChatTransport pointant vers http://localhost:{port}/api/chat.
    1.6  Frontend : Rendre les messages via message.parts (part.type === "text" → afficher part.text).
    1.7  Frontend : Construire l'UI de chat (liste de messages, zone de saisie, indicateur de streaming).
    1.8  Frontend : Styling Tailwind — design épuré, bulle utilisateur vs bulle agent.
    1.9  Gérer la clé API DeepSeek : l'utilisateur la saisit dans un écran de settings, stockée localement (Tauri Store plugin ou fichier de config).

    Livrables :
    - Un chat fonctionnel qui stream les réponses de DeepSeek en temps réel.
    - Pas encore de tools, pas de mémoire — juste de la conversation pure.

    Definition of Done : L'utilisateur envoie "Bonjour", DeepSeek répond mot par mot en streaming dans le chat.

────────────────────────────────────────────────────────────────

PHASE 2 — La Boucle Agentique & Les Premiers Outils

    Objectif : L'Agent peut appeler des outils et boucler (raisonner → agir → observer → raisonner).

    Dépendance : Phase 1 terminée.

    Tâches :
    2.1  Backend : Implémenter la boucle agentique dans /api/chat :
         - Envoyer les messages + la liste des tools (JSON Schema) à DeepSeek.
         - Si DeepSeek renvoie un tool_call pour un server-side tool → exécuter l'outil → renvoyer le résultat à DeepSeek → boucler (dans la même requête).
         - Si DeepSeek renvoie un tool_call pour un client-side tool → streamer tool-input-available → fermer le flux. Le frontend relancera une nouvelle requête avec le résultat via addToolOutput().
         - Si DeepSeek renvoie du texte → streamer les text-delta au frontend → fin.
         - Séparer chaque itération par des événements SSE start-step / finish-step.
         Note veille technique : La boucle agentique est "hybride" — elle boucle en interne pour les tools serveur, mais se coupe et reprend via une nouvelle requête HTTP pour les tools client (QCM, email). Le backend reste stateless entre les requêtes.
    2.2  Backend : Implémenter le Circuit Breaker (max_steps = 5 par requête).
         ⚠️ Premortem §4 : couper la boucle après N itérations.
    2.3  Backend : Implémenter le Workspace Jail — toutes les opérations fichiers sont confinées dans le dossier projet.
         ⚠️ Brief §6 : vérification stricte des chemins (pas de ../ ni de chemins absolus hors périmètre).
    2.4  Backend : Gestion d'Erreurs Verbeuse — chaque outil renvoie un message d'erreur lisible par le LLM (pas de crash brut).
         ⚠️ Premortem §4 : format "Erreur : ... Voici les alternatives : [...]"
    2.5  Implémenter les 4 outils fichiers de base :
         - list_project_files(directory_path)
         - read_file_content(file_name)
         - write_project_note(title, markdown_content)
         - write_json_table(table_name, json_data)
    2.6  Frontend : Afficher les appels d'outils dans le chat via les typed tool parts du SDK.
         Chaque tool_call est rendu comme un case "tool-nomDeLoutil" dans message.parts avec ses états (input-streaming → input-available → output-available).
    2.7  Frontend : Configurer sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithToolCalls pour que le SDK relance automatiquement la boucle quand un client-side tool est résolu.
    2.8  Concept de "Projet" : l'utilisateur crée un projet (= un dossier isolé dans ~/VibetaffProjects/NomDuProjet/).

    Livrables :
    - L'Agent raisonne, appelle des outils fichiers, et continue la conversation avec les résultats.
    - Le circuit breaker coupe les boucles infinies.

    Definition of Done : L'utilisateur dit "Crée une note résumé du projet", l'Agent appelle write_project_note, le fichier apparaît dans le dossier. La boucle s'arrête après max_steps si l'Agent tourne en rond.

────────────────────────────────────────────────────────────────

PHASE 3 — Le Pipeline d'Ingestion de Documents

    Objectif : L'utilisateur glisse un PDF/Excel/Email, le document est indexé et interrogeable.

    Dépendance : Phase 2 terminée.

    Tâches :
    3.1  Frontend : Zone de drag & drop pour déposer des fichiers dans le projet.
    3.2  Frontend : Upload des fichiers vers le backend (POST /api/project/{id}/ingest).
    3.3  Backend : Module d'extraction — dispatche selon le type de fichier :
         - .pdf / .docx → PyMuPDF4LLM → Markdown.
         - .xlsx / .csv → pandas + openpyxl → Tableaux Markdown.
         - .eml / .msg → BeautifulSoup → Texte structuré (De, À, Date, Sujet, Corps).
         - Pièces jointes d'emails → sauvegardées et réinjectées dans le pipeline.
    3.4  Backend : Module de chunking sémantique :
         - Découpage en chunks de ~800 tokens.
         - Répétition obligatoire des en-têtes de tableau dans chaque chunk.
           ⚠️ Premortem §3 : règle anti-hallucination tabulaire.
         - Métadonnées attachées (nom fichier, type, date, numéro de page).
    3.5  Backend : Module d'embedding :
         - Charger sentence-transformers (all-MiniLM-L6-v2) au démarrage du sidecar.
         - Transformer chaque chunk en vecteur.
    3.6  Backend : Module de stockage LanceDB :
         - Créer une table par projet.
         - Insérer vecteurs + texte + métadonnées.
    3.7  Frontend : Barre de progression de l'ingestion + liste des documents du projet.
    3.8  Tester avec des fichiers réels : un PDF de 50 pages, un Excel de 500 lignes, un .eml.

    Livrables :
    - Le pipeline Extraction → Chunking → Embedding → LanceDB fonctionne de bout en bout.
    - L'utilisateur voit ses documents listés dans le projet après ingestion.

    Definition of Done : Glisser un PDF de bilan financier → le document est indexé → l'Agent peut répondre à "Quel est le chiffre d'affaires 2024 ?" en citant le bon passage.

────────────────────────────────────────────────────────────────

PHASE 4 — Le RAG & La Mémoire

    Objectif : L'Agent sait chercher dans les documents et se souvient des préférences.

    Dépendance : Phase 3 terminée.

    Tâches :
    4.1  Backend : Implémenter l'outil query_project_memory(question) :
         - Transformer la question en vecteur (sentence-transformers).
         - Chercher les top-K chunks les plus proches dans LanceDB.
         - Renvoyer le texte des chunks + métadonnées au LLM.
    4.2  Backend : Implémenter la base SQLite pour la mémoire à long terme :
         - Table projects (id, name, created_at, path).
         - Table conversations (id, project_id, messages JSON, created_at).
         - Table memory (id, project_id, key, value, created_at).
    4.3  Backend : Implémenter l'outil save_to_long_term_memory(key, value).
    4.4  Backend : Au début de chaque requête chat, injecter automatiquement les mémoires du projet dans le system prompt.
    4.5  Backend : Sauvegarder l'historique de chaque conversation dans SQLite.
    4.6  Frontend : Sidebar avec la liste des projets et l'historique des conversations.
    4.7  Frontend : Possibilité de créer un nouveau projet / reprendre une ancienne conversation.

    Livrables :
    - L'Agent retrouve des infos dans les documents indexés.
    - Les préférences utilisateur persistent entre les sessions.
    - L'historique des chats est sauvegardé et rechargeable.

    Definition of Done : Fermer l'app, la rouvrir → les conversations et mémoires sont toujours là. L'Agent dit "Je me souviens que tu préfères les montants en k€" si c'était mémorisé avant.

────────────────────────────────────────────────────────────────

PHASE 5 — Les Outils Avancés

    Objectif : L'Agent peut chercher sur le web, exécuter du calcul, et préparer des emails.

    Dépendance : Phase 4 terminée.

    Tâches :
    5.1  Backend : Implémenter web_search(query) via l'API Tavily.
         - Appel HTTP vers Tavily → résumé + sources.
         - Clé API Tavily à configurer dans les settings (comme DeepSeek).
    5.2  Backend : Implémenter draft_email(to, subject, body).
         - L'outil renvoie les données au frontend via le flux SSE.
         - Pas d'envoi direct — le frontend affiche un composant (voir Phase 6).
    5.3  Backend : Implémenter run_local_calculation(python_code) via sandbox WASM.
         ⚠️ Premortem §5 : JAMAIS exec()/eval(). Utiliser Pyodide ou wasmtime-py.
         - Installer et configurer la sandbox WASM.
         - Le code LLM entre comme String → exécuté dans la sandbox → résultat sort comme String.
         - Timeout de 30 secondes max par exécution.
         - Librairies autorisées dans la sandbox : math, statistics, json, csv, re (pas d'accès réseau/fichiers).
    5.4  Tester le workflow "Map-Reduce" :
         ⚠️ Premortem §3 : l'Agent doit déléguer les gros calculs à run_local_calculation plutôt que tout charger dans son contexte.

    Livrables :
    - 9 outils opérationnels au total (4 fichiers + 3 analyse/mémoire + 2 communication).
    - Le code généré par l'Agent s'exécute dans un bac à sable sécurisé.

    Definition of Done : L'utilisateur dit "Cherche le cours EUR/USD et calcule la conversion de mon devis". L'Agent utilise web_search + run_local_calculation et renvoie le résultat.

────────────────────────────────────────────────────────────────

PHASE 6 — La Generative UI

    Objectif : Les outils affichent des composants interactifs dans le chat, pas juste du texte.

    Dépendance : Phase 5 terminée.

    Tâches :
    6.1  Frontend : Composant DataGrid (Tableau Interactif).
         - Reçoit un JSON de données depuis le tool_call write_json_table.
         - Affiche un tableau triable par colonnes (clic sur l'en-tête).
         - Bouton "Copier CSV" qui copie le contenu dans le presse-papier.
         - Cellules éditables par l'utilisateur.
    6.2  Frontend : Composant AskHuman (QCM) — client-side tool.
         - L'Agent appelle le tool ask_human → le SDK affiche le composant via case "tool-ask_human".
         - Le chat affiche des boutons radio / boutons de choix (état input-available).
         - Le choix de l'utilisateur est renvoyé via addToolOutput() → le SDK relance la requête automatiquement.
    6.3  Frontend : Composant EmailDraft (Brouillon d'email) — client-side tool.
         - L'Agent appelle draft_email → le SDK affiche le composant via case "tool-draft_email" (état input-available).
         - Champs éditables : destinataire, objet, corps.
         - Bouton [Envoyer] → ouvre le client mail natif via lien mailto: pré-rempli.
         - L'utilisateur valide via addToolOutput() → la boucle reprend.
    6.4  Frontend : Composant LiveDiff (Vue des modifications) — custom data part.
         - Backend envoie un événement SSE type: "data-diff" avec le contenu avant/après.
         - Affiche les lignes supprimées (rouge) et ajoutées (vert).
         - Utilisé quand l'Agent modifie une note existante via write_project_note.
    6.5  Backend + Frontend : Implémenter le flux d'approbation pour les outils dangereux :
         ⚠️ Premortem §2 mis à jour : on utilise le mécanisme natif du Vercel AI SDK (pas asyncio.Event + UUID).
         - Backend : déclarer write_project_note (si fichier existant) avec needsApproval: true dans la liste des tools.
         - Frontend : quand l'outil est en état "approval-requested", afficher un bouton Approuver/Refuser.
         - L'utilisateur clique → addToolApprovalResponse() → le SDK relance la requête → le backend exécute l'outil.
         - Configurer sendAutomaticallyWhen: lastAssistantMessageIsCompleteWithApprovalResponses.
    6.6  Frontend : Rendre chaque composant via les typed tool parts du SDK (case "tool-nomDeLoutil" dans message.parts.map()).

    Livrables :
    - Le chat affiche des tableaux interactifs, des QCM, des brouillons d'email et des diffs.
    - Le flux d'approbation humaine fonctionne sans bloquer le serveur.

    Definition of Done : L'Agent génère un tableau → il s'affiche triable dans le chat. L'Agent demande une clarification → des boutons apparaissent. L'Agent prépare un email → le brouillon est éditable et le bouton Envoyer ouvre Apple Mail.

────────────────────────────────────────────────────────────────

PHASE 7 — Sécurité & Robustesse

    Objectif : L'app est blindée contre les comportements dangereux de l'Agent.

    Dépendance : Phase 6 terminée.

    Tâches :
    7.1  Audit du Workspace Jail : tester avec des chemins malveillants (../../etc/passwd, liens symboliques, chemins absolus hors périmètre).
    7.2  Audit de la sandbox WASM : tester avec du code malveillant (import os, import subprocess, open('/etc/passwd'), socket, requests...).
    7.3  Audit du Human-in-the-Loop : vérifier que TOUTE action destructrice (écraser un fichier, envoyer un mail) exige une validation.
    7.4  Ajouter un rate limiter sur les appels DeepSeek (éviter l'explosion de coûts si boucle mal coupée).
    7.5  Validation des entrées : tailles de fichiers max (100 Mo), longueur de messages max, types de fichiers autorisés.
    7.6  Logs de sécurité : journaliser toutes les actions de l'Agent dans un fichier local (horodaté).
    7.7  Tester le circuit breaker avec des scénarios de boucle infinie volontaire.

    Livrables :
    - Rapport de tests de sécurité (checklist passée).
    - Aucun moyen pour l'Agent de sortir de sa prison.

    Definition of Done : Aucun des tests malveillants ne passe. L'Agent ne peut ni lire hors du projet, ni exécuter du code dangereux, ni agir sans validation humaine.

────────────────────────────────────────────────────────────────

PHASE 8 — Packaging & Distribution macOS

    Objectif : Un fichier .dmg que n'importe qui peut installer en double-cliquant.

    Dépendance : Phase 7 terminée.

    Tâches :
    8.1  Compiler le backend Python avec PyInstaller (--onefile, cible aarch64-apple-darwin pour Mac M1+).
    8.2  Renommer le binaire avec le target triple Tauri (ex: vibetaff-backend-aarch64-apple-darwin).
    8.3  Placer le binaire dans src-tauri/binaries/.
    8.4  Configurer tauri.conf.json : externalBin, bundle, icône, nom d'app, version.
    8.5  Implémenter le lifecycle du sidecar :
         - Au lancement : Tauri spawn le sidecar → attend le /health → affiche l'app.
         - À la fermeture : Tauri tue proprement le process sidecar (SIGTERM).
    8.6  Écran de première utilisation (onboarding) :
         - Saisie de la clé API DeepSeek (obligatoire).
         - Saisie de la clé API Tavily (optionnelle, la recherche web est désactivée sans).
    8.7  Builder le .dmg avec npm run tauri build.
    8.8  Tester l'installation sur un Mac "vierge" (sans Python, sans Node).
    8.9  (Optionnel) Signature du code avec un certificat Apple Developer pour éviter le warning Gatekeeper.

    Livrables :
    - Un fichier Vibetaff.dmg (~80-120 Mo).
    - Installation : glisser dans Applications → double-clic → ça marche.

    Definition of Done : Un Mac sans aucun outil de dev installé exécute Vibetaff via le .dmg. Le sidecar démarre, le chat fonctionne, les documents s'ingèrent.

────────────────────────────────────────────────────────────────

PHASE 9 — Polish & UX Final

    Objectif : L'app est agréable à utiliser, les cas limites sont gérés.

    Dépendance : Phase 8 terminée.

    Tâches :
    9.1  UX Loading States : indicateurs clairs pendant l'ingestion, le streaming, les appels d'outils.
    9.2  UX Erreurs : messages d'erreur humains (pas de stack traces) — "La connexion à DeepSeek a échoué. Vérifie ta clé API dans les paramètres."
    9.3  Animations : transitions fluides sur les messages, les composants Generative UI.
    9.4  Raccourcis clavier : Cmd+N (nouveau projet), Cmd+Enter (envoyer message), Cmd+K (search).
    9.5  Mode sombre / clair selon les préférences système macOS.
    9.6  Performance : optimiser le temps de démarrage du sidecar (pré-charger le modèle d'embeddings).
    9.7  Gestion des gros fichiers : barre de progression, chunking en arrière-plan, notification quand c'est prêt.
    9.8  Workflow complet de test :
         - Reproduire le scénario du brief §7 (l'Aha Moment) :
           Créer projet "Audit Omega" → déposer 3 PDF + 1 Excel + 2 emails
           → "Compare l'EBITDA, vérifie les taux de change, fais un tableau, prépare un mail"
           → Valider que tout fonctionne de bout en bout.

    Livrables :
    - App prête pour des beta-testeurs.
    - Le scénario "Aha Moment" du brief passe sans accroc.

    Definition of Done : 3 utilisateurs non-techniques testent l'app sans aide et réussissent le workflow complet.

────────────────────────────────────────────────────────────────

ANNEXE — Vue d'ensemble des dépendances

    Phase 0  Fondations (Tauri + React + FastAPI)
      ↓
    Phase 1  Chat en Streaming (DeepSeek + SSE + useChat)
      ↓
    Phase 2  Boucle Agentique + Outils Fichiers (Tool Calling + Circuit Breaker)
      ↓
    Phase 3  Pipeline d'Ingestion (PDF/Excel/Email → LanceDB)
      ↓
    Phase 4  RAG & Mémoire (Recherche sémantique + SQLite + Historique)
      ↓
    Phase 5  Outils Avancés (Tavily + Sandbox WASM + Email Draft)
      ↓
    Phase 6  Generative UI (DataGrid + QCM + Diff + Human-in-the-Loop)
      ↓
    Phase 7  Sécurité & Robustesse (Audit + Tests malveillants)
      ↓
    Phase 8  Packaging macOS (PyInstaller + .dmg)
      ↓
    Phase 9  Polish & UX Final (Le "Aha Moment" passe)

────────────────────────────────────────────────────────────────

ANNEXE — Stack Technique Complète (Récapitulatif)

    Catégorie              Techno                      Rôle
    ─────────              ─────                       ────
    App Shell              Tauri v2                    Conteneur desktop natif macOS
    Frontend               React + TypeScript          Interface utilisateur
    Styling                Tailwind CSS                Design system
    Streaming UI           Vercel AI SDK (ai/react)    Hook useChat, Generative UI
    Backend                FastAPI (Python)            API locale, orchestration Agent
    Packaging Backend      PyInstaller (--onefile)     Exécutable autonome sans Python
    LLM                    DeepSeek V3 (API)           Raisonnement + Tool Calling
    Extraction PDF         PyMuPDF4LLM                 PDF/Word → Markdown
    Extraction Excel       pandas + openpyxl           Excel/CSV → Markdown
    Extraction Email       BeautifulSoup               HTML email → texte structuré
    Embeddings             sentence-transformers       Texte → Vecteurs (local, gratuit)
    Base Vectorielle       LanceDB                     Stockage + recherche sémantique
    Base Relationnelle     SQLite                      Historique, mémoire, projets
    Recherche Web          Tavily API                  Recherche optimisée IA
    Sandbox Code           Pyodide / wasmtime-py       Exécution Python en bac à sable WASM
    Sécurité               Workspace Jail + HITL       Confinement + validation humaine

────────────────────────────────────────────────────────────────

ANNEXE — Feuille de Route V2 (Post-MVP)

Objectif : Après le MVP V1 (Phases 0-9), VibeTaff s'ouvre à l'écosystème communautaire
et ajoute les fonctionnalités repoussées volontairement.

V2.1 — Client MCP (Model Context Protocol)
    - Intégrer le SDK Python MCP (modelcontextprotocol/python-sdk, v1.26+)
    - Le backend FastAPI devient un "MCP Host" : il peut se connecter à des MCP servers externes
    - Interface de configuration dans les Paramètres : l'utilisateur ajoute un MCP server (local ou distant)
    - Les outils exposés par le MCP server apparaissent automatiquement dans la liste d'outils de l'agent
    - Priorité : Gmail, Google Calendar, Notion, Slack (skills les plus populaires de ClawHub)

V2.2 — Email Natif (OAuth)
    - Remplacer le mailto: V1 par une intégration OAuth Gmail / Outlook
    - L'agent peut envoyer des emails directement (avec Human-in-the-Loop pour approbation)
    - Lecture de boîte de réception pour contexte (via MCP server Gmail ou intégration native)

V2.3 — Multi-plateforme
    - Packaging Windows (.msi) et Linux (.AppImage/.deb)
    - Adapter les chemins, permissions, et le lancement du sidecar pour chaque OS
    - CI/CD pour builds automatisés multi-plateforme

V2.4 — Multi-LLM
    - Support de plusieurs providers : Claude (Anthropic), GPT (OpenAI), modèles locaux (Ollama)
    - Sélecteur de modèle dans les Paramètres
    - Gestion unifiée des formats de tool calling (chaque provider a ses variantes)

V2.5 — OCR & Documents Scannés
    - Intégrer un moteur OCR (Tesseract ou équivalent) dans le pipeline d'ingestion
    - Détecter automatiquement les PDF "images" (pas de texte extractible) et les passer en OCR
    - Ajouter les résultats OCR au même pipeline chunking → embedding → LanceDB

V2.6 — Marketplace MCP
    - Interface graphique de découverte de MCP servers pré-configurés
    - Installation en un clic depuis un catalogue curé
    - Inspiration : ClawHub (5 700+ skills), mais adapté au desktop
