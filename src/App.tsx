import { useState, useEffect, useCallback } from "react";
import Chat from "./components/Chat";
import Settings from "./components/Settings";

const BACKEND_URL = "http://localhost:11434";
const PROJECT_ID = "default";

function App() {
  const [backendStatus, setBackendStatus] = useState<
    "connecting" | "connected" | "error"
  >("connecting");
  const [deepseekConfigured, setDeepseekConfigured] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<{ name: string; status: "indexing" | "ready" | "error" }[]>([]);

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

  const startNewConversation = useCallback(async () => {
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/project/${PROJECT_ID}/conversations`,
        { method: "POST" }
      );
      const data = await res.json();
      setConversationId(data.conversation_id);
    } catch {
      setConversationId(null);
    }
  }, []);

  useEffect(() => {
    if (backendStatus === "connected" && deepseekConfigured && !conversationId) {
      startNewConversation();
    }
  }, [backendStatus, deepseekConfigured, conversationId, startNewConversation]);

  const handleNewChat = useCallback(() => {
    setConversationId(null);
    startNewConversation();
  }, [startNewConversation]);

  const ingestFile = useCallback(async (file: File) => {
    const entry = { name: file.name, status: "indexing" as const };
    setPendingFiles(prev => [...prev, entry]);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(
        `${BACKEND_URL}/api/project/${PROJECT_ID}/ingest`,
        { method: "POST", body: formData }
      );
      const data = await res.json();
      if (data.status === "ok") {
        setPendingFiles(prev =>
          prev.map(f => f.name === file.name ? { ...f, status: "ready" as const } : f)
        );
      } else {
        setPendingFiles(prev =>
          prev.map(f => f.name === file.name ? { ...f, status: "error" as const } : f)
        );
      }
    } catch {
      setPendingFiles(prev =>
        prev.map(f => f.name === file.name ? { ...f, status: "error" as const } : f)
      );
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      Array.from(e.dataTransfer.files).forEach(ingestFile);
    },
    [ingestFile]
  );

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
    <div
      className="min-h-screen bg-zinc-950 flex flex-col relative"
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target || !e.currentTarget.contains(e.relatedTarget as Node)) {
          setIsDragOver(false);
        }
      }}
      onDrop={handleDrop}
    >
      <header className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-zinc-100">Vibetaff</h1>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleNewChat}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Nouvelle conversation"
          >
            + Nouveau
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Paramètres
          </button>
        </div>
      </header>

      {conversationId && (
        <Chat
          key={conversationId}
          backendUrl={BACKEND_URL}
          conversationId={conversationId}
          projectId={PROJECT_ID}
          onIngestFile={ingestFile}
          pendingFiles={pendingFiles.map(f => f.name)}
          pendingFileStatuses={pendingFiles}
          onClearPendingFiles={() => setPendingFiles([])}
        />
      )}

      {isDragOver && (
        <div className="absolute inset-0 z-50 bg-zinc-500/5 backdrop-blur-sm border-2 border-dashed border-zinc-600 flex items-center justify-center pointer-events-none">
          <div className="bg-zinc-900/90 rounded-2xl px-8 py-6 text-center">
            <div className="text-4xl mb-3 text-zinc-400">+</div>
            <p className="text-zinc-300 font-medium">Déposez vos fichiers</p>
            <p className="text-zinc-500 text-sm mt-1">PDF, Word, Excel, CSV, Email</p>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
