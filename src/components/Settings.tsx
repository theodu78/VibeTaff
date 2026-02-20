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
            ? "Pour commencer, configure ta clé API DeepSeek."
            : "Configuration de l'application."}
        </p>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-4">
          <div>
            <h3 className="text-sm font-medium text-zinc-300 mb-2">
              Clé API DeepSeek
            </h3>
            <p className="text-xs text-zinc-500 mb-3">
              Crée un fichier <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-300">backend/.env</code> avec
              le contenu suivant :
            </p>
            <pre className="bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-sm text-emerald-400 font-mono">
              DEEPSEEK_API_KEY=sk-ta-cle-ici
            </pre>
          </div>

          <div className="pt-2">
            <p className="text-xs text-zinc-500 mb-4">
              Puis relance le backend Python. Quand c'est fait, clique ci-dessous.
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
