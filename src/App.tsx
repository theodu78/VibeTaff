import { useState, useEffect } from "react";
import Chat from "./components/Chat";
import Settings from "./components/Settings";

const BACKEND_URL = "http://localhost:11434";

function App() {
  const [backendStatus, setBackendStatus] = useState<
    "connecting" | "connected" | "error"
  >("connecting");
  const [deepseekConfigured, setDeepseekConfigured] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/health`);
        if (res.ok) {
          const data = await res.json();
          setBackendStatus("connected");
          setDeepseekConfigured(data.deepseek_configured);
        } else {
          setBackendStatus("error");
        }
      } catch {
        setBackendStatus("error");
      }
    };

    checkBackend();
    const interval = setInterval(checkBackend, 10000);
    return () => clearInterval(interval);
  }, []);

  if (backendStatus !== "connected") {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center">
        <h1 className="text-4xl font-bold mb-2">Vibetaff</h1>
        <p className="text-zinc-400 mb-8">
          Le Cursor des travailleurs du savoir
        </p>
        <div className="flex items-center gap-3 px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              backendStatus === "connecting"
                ? "bg-amber-500 animate-pulse"
                : "bg-red-500"
            }`}
          />
          <span className="text-sm text-zinc-300">
            {backendStatus === "connecting"
              ? "Connexion au backend..."
              : "Backend hors ligne"}
          </span>
        </div>
      </div>
    );
  }

  if (!deepseekConfigured || showSettings) {
    return (
      <Settings
        onDone={() => {
          setShowSettings(false);
          setDeepseekConfigured(true);
        }}
        isFirstTime={!deepseekConfigured}
      />
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col">
      <header className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-zinc-100">Vibetaff</h1>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          Paramètres
        </button>
      </header>

      <Chat backendUrl={BACKEND_URL} />
    </div>
  );
}

export default App;
