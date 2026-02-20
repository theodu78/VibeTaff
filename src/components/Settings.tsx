interface SettingsProps {
  onDone: () => void;
  isFirstTime: boolean;
}

export default function Settings({ onDone, isFirstTime }: SettingsProps) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center p-8">
      <div className="max-w-md w-full">
        <h1 className="text-3xl font-bold mb-2">
          {isFirstTime ? "Bienvenue sur Vibetaff" : "Paramètres"}
        </h1>
        <p className="text-zinc-400 mb-8">
          {isFirstTime
            ? "Pour commencer, configure tes clés API."
            : "Configuration de l'application."}
        </p>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-medium text-zinc-300 mb-2">
              Clé API DeepSeek
              <span className="ml-2 text-xs text-red-400 font-normal">obligatoire</span>
            </h3>
            <p className="text-xs text-zinc-500 mb-3">
              Obtiens ta clé sur{" "}
              <a
                href="https://platform.deepseek.com"
                target="_blank"
                rel="noopener"
                className="text-blue-400 hover:underline"
              >
                platform.deepseek.com
              </a>
            </p>
            <pre className="bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-sm text-emerald-400 font-mono whitespace-pre-wrap">
DEEPSEEK_API_KEY=sk-ta-cle-ici</pre>
          </div>

          <div>
            <h3 className="text-sm font-medium text-zinc-300 mb-2">
              Clé API Tavily
              <span className="ml-2 text-xs text-zinc-600 font-normal">optionnelle</span>
            </h3>
            <p className="text-xs text-zinc-500 mb-3">
              Pour la recherche web. Gratuit (1 000 req/mois) sur{" "}
              <a
                href="https://tavily.com"
                target="_blank"
                rel="noopener"
                className="text-blue-400 hover:underline"
              >
                tavily.com
              </a>
            </p>
            <pre className="bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-400 font-mono whitespace-pre-wrap">
TAVILY_API_KEY=tvly-ta-cle-ici</pre>
          </div>

          <div className="border-t border-zinc-800 pt-4">
            <p className="text-xs text-zinc-500 mb-1">
              Ajoute ces clés dans le fichier :
            </p>
            <code className="text-xs bg-zinc-800 px-2 py-1 rounded text-zinc-300 block mb-4">
              backend/.env
            </code>
            <p className="text-xs text-zinc-500 mb-4">
              Puis relance le backend si nécessaire.
            </p>
            <button
              onClick={onDone}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-4 py-3 text-sm font-medium transition-colors"
            >
              C'est fait, continuer
            </button>
          </div>
        </div>

        {!isFirstTime && (
          <button
            onClick={onDone}
            className="mt-4 w-full text-zinc-500 hover:text-zinc-300 text-sm transition-colors"
          >
            Retour au chat
          </button>
        )}
      </div>
    </div>
  );
}
