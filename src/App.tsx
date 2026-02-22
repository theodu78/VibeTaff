import { useState, useEffect, useCallback } from "react";
import Chat from "./components/Chat";
import Settings from "./components/Settings";
import CommandPalette from "./components/CommandPalette";
import ConversationSidebar from "./components/ConversationSidebar";

const BACKEND_URL = "http://localhost:11434";
const PROJECT_ID = "default";

function App() {
  const [backendStatus, setBackendStatus] = useState<
    "connecting" | "connected" | "error"
  >("connecting");
  const [llmConfigured, setLlmConfigured] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<{ name: string; status: "indexing" | "ready" | "error" }[]>([]);
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [openFilePath, setOpenFilePath] = useState<string | null>(null);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/health`);
        if (res.ok) {
          const data = await res.json();
          setBackendStatus("connected");
          setLlmConfigured(data.deepseek_configured || data.llm_configured);
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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "p") {
        e.preventDefault();
        setCmdPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
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
    if (backendStatus === "connected" && llmConfigured && !conversationId) {
      startNewConversation();
    }
  }, [backendStatus, llmConfigured, conversationId, startNewConversation]);

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

  if (!llmConfigured || showSettings) {
    return (
      <Settings
        onDone={() => {
          setShowSettings(false);
          setLlmConfigured(true);
        }}
        isFirstTime={!llmConfigured}
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
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-800/50"
            title="Historique"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-sm font-semibold text-zinc-100">Vibetaff</h1>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCmdPaletteOpen(true)}
            className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors px-2 py-1 rounded hover:bg-zinc-800/50"
            title="Rechercher un fichier (⌘P)"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span className="hidden sm:inline">Rechercher</span>
            <kbd className="text-[10px] text-zinc-600 bg-zinc-800 px-1 rounded font-mono ml-1">⌘P</kbd>
          </button>
          <button
            onClick={handleNewChat}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
            title="Nouvelle conversation"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nouveau
          </button>
          <button
            onClick={() => setShowSettings(true)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Paramètres
          </button>
        </div>
      </header>

      <ConversationSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        backendUrl={BACKEND_URL}
        projectId={PROJECT_ID}
        currentConversationId={conversationId}
        onSelectConversation={(id) => setConversationId(id)}
        onNewChat={handleNewChat}
        onDeleteConversation={(id) => {
          if (id === conversationId) handleNewChat();
        }}
      />

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
          externalFilePath={openFilePath}
          onClearExternalFile={() => setOpenFilePath(null)}
        />
      )}

      <CommandPalette
        open={cmdPaletteOpen}
        onClose={() => setCmdPaletteOpen(false)}
        backendUrl={BACKEND_URL}
        projectId={PROJECT_ID}
        onOpenFile={(path) => setOpenFilePath(path)}
        onNewChat={handleNewChat}
        onOpenSettings={() => setShowSettings(true)}
      />

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
