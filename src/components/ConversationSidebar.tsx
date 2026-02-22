import { useState, useEffect, useCallback, useMemo } from "react";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ConversationSidebarProps {
  open: boolean;
  onClose: () => void;
  backendUrl: string;
  projectId: string;
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
}

export default function ConversationSidebar({
  open,
  onClose,
  backendUrl,
  projectId,
  currentConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/project/${projectId}/conversations`);
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, [backendUrl, projectId]);

  useEffect(() => {
    if (open) fetchConversations();
  }, [open, fetchConversations]);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    const q = searchQuery.toLowerCase();
    return conversations.filter(
      (c) =>
        (c.title || "").toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q)
    );
  }, [conversations, searchQuery]);

  const handleDelete = async (id: string) => {
    try {
      await fetch(`${backendUrl}/api/conversations/${id}`, { method: "DELETE" });
      onDeleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch { /* ignore */ }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return "À l'instant";
      if (diffMin < 60) return `Il y a ${diffMin}min`;
      const diffH = Math.floor(diffMin / 60);
      if (diffH < 24) return `Il y a ${diffH}h`;
      const diffD = Math.floor(diffH / 24);
      if (diffD < 7) return `Il y a ${diffD}j`;
      return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
    } catch {
      return "";
    }
  };

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="fixed left-0 top-0 bottom-0 w-72 bg-zinc-950 border-r border-zinc-800 z-50 flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-200">Conversations</h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-3 py-2">
          <button
            onClick={() => { onNewChat(); onClose(); }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-zinc-300 bg-zinc-800/50 hover:bg-zinc-700/50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nouvelle conversation
          </button>
        </div>

        <div className="px-3 pb-2">
          <input
            type="text"
            placeholder="Rechercher..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-800/50 border border-zinc-700/50 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-600"
          />
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          {loading && conversations.length === 0 && (
            <div className="text-center text-zinc-600 text-xs py-4 animate-pulse">
              Chargement...
            </div>
          )}
          {!loading && filtered.length === 0 && (
            <div className="text-center text-zinc-600 text-xs py-4">
              {searchQuery ? "Aucun résultat" : "Aucune conversation"}
            </div>
          )}
          {filtered.map((conv) => {
            const isCurrent = conv.id === currentConversationId;
            return (
              <div
                key={conv.id}
                className={`group flex items-center justify-between px-3 py-2 rounded-lg mb-0.5 cursor-pointer transition-colors ${
                  isCurrent
                    ? "bg-zinc-800 text-zinc-100"
                    : "text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200"
                }`}
                onClick={() => { onSelectConversation(conv.id); onClose(); }}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">
                    {conv.title || "Sans titre"}
                  </p>
                  <p className="text-[10px] text-zinc-600 mt-0.5">
                    {formatDate(conv.updated_at)}
                  </p>
                </div>
                {!isCurrent && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(conv.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all ml-2"
                    title="Supprimer"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
