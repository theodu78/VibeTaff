import { useRef, useEffect, useState, useMemo, useCallback } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import ToolCall from "./ToolCall";
import Markdown, { FileOpenContext } from "./Markdown";
import ApprovalCard from "./ApprovalCard";
import ThinkingBlock from "./ThinkingBlock";
import FileViewer from "./FileViewer";
import TodoBlock from "./TodoBlock";
import TodoViewer from "./TodoViewer";

interface ChatProps {
  backendUrl: string;
  conversationId: string;
  projectId: string;
  onIngestFile?: (file: File) => void;
  pendingFiles?: string[];
  onClearPendingFiles?: () => void;
}

export default function Chat({
  backendUrl,
  conversationId,
  projectId,
  onIngestFile,
  pendingFiles = [],
  onClearPendingFiles,
}: ChatProps) {
  const [input, setInput] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [viewerPath, setViewerPath] = useState<string | null>(null);
  const [todoViewerOpen, setTodoViewerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${backendUrl}/api/chat`,
        body: { conversation_id: conversationId, project_id: projectId },
      }),
    [backendUrl, conversationId, projectId]
  );

  const { messages, sendMessage, status, error } = useChat({ transport });

  const isStreaming = status === "streaming";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    let messageText = input;
    if (pendingFiles.length > 0) {
      const filesStr = pendingFiles.map(f => `"${f}"`).join(", ");
      messageText = `[Fichier(s) joint(s) : ${filesStr}]\n\n${input}`;
      onClearPendingFiles?.();
    }

    sendMessage({ text: messageText });
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleCopy = useCallback(async (messageId: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(messageId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch { /* */ }
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || !onIngestFile) return;
      Array.from(files).forEach(onIngestFile);
      e.target.value = "";
    },
    [onIngestFile]
  );

  const getMessageText = (parts: (typeof messages)[number]["parts"]) =>
    parts
      .filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join("\n");

  const lastUserIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") return i;
    }
    return -1;
  })();

  const handleFileOpen = useCallback((path: string) => {
    setViewerPath(path);
  }, []);

  return (
    <FileOpenContext.Provider value={handleFileOpen}>
    <div className="flex-1 flex flex-col min-h-0">

      {/* ═══ SCROLLABLE: everything in one scroll ═══ */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-3">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full min-h-[50vh] text-center">
              <h2 className="text-2xl font-bold text-zinc-100 mb-2">
                Vibetaff
              </h2>
              <p className="text-zinc-500 max-w-md text-sm">
                Posez une question ou décrivez ce que vous voulez accomplir.
              </p>
            </div>
          )}

          {messages.map((message, msgIdx) => {
            const isUser = message.role === "user";
            const isLastUser = msgIdx === lastUserIdx;

            if (isUser) {
              if (isLastUser) {
                return (
                  <div
                    key={message.id}
                    className="sticky top-0 z-10 -mx-4 px-4 bg-zinc-950"
                  >
                    <div className="max-w-3xl mx-auto pt-3">
                      <div className="bg-zinc-800/60 border border-zinc-700/40 rounded-xl px-4 py-3">
                        <p className="text-sm text-zinc-200 whitespace-pre-wrap">
                          {getMessageText(message.parts)}
                        </p>
                      </div>
                    </div>
                    <div className="h-2 bg-gradient-to-b from-zinc-950 to-transparent" />
                  </div>
                );
              }
              return (
                <div key={message.id}>
                  <div className="bg-zinc-800/30 border border-zinc-700/20 rounded-xl px-4 py-3">
                    <p className="text-sm text-zinc-400 whitespace-pre-wrap">
                      {getMessageText(message.parts)}
                    </p>
                  </div>
                </div>
              );
            }

            /* ─── Assistant message ─── */

            const isLastMsg = msgIdx === messages.length - 1;
            const isActivelyStreaming = isStreaming && isLastMsg;

            const allReasoningText = message.parts
              .filter((p) => p.type === "reasoning")
              .map((p) => (p as { text: string }).text || "")
              .join("\n");

            const hasTextContent = message.parts.some(
              (p) => p.type === "text" && p.text.trim().length > 0
            );

            const thinkingIsStreaming =
              isActivelyStreaming && !hasTextContent;

            const nonReasoningParts = message.parts.filter(
              (p) => p.type !== "reasoning"
            );

            return (
              <div key={message.id} className="group relative">
                {(allReasoningText || thinkingIsStreaming) && (
                  <ThinkingBlock
                    text={allReasoningText}
                    isStreaming={thinkingIsStreaming}
                  />
                )}

                {nonReasoningParts.map((part, i) => {
                  switch (part.type) {
                    case "text":
                      return (
                        <Markdown key={`${message.id}-${i}`}>
                          {part.text}
                        </Markdown>
                      );
                    case "dynamic-tool":
                      return (
                        <ToolCall
                          key={`${message.id}-${i}`}
                          toolName={part.toolName}
                          state={part.state}
                          input={
                            "input" in part
                              ? (part.input as Record<string, unknown>)
                              : undefined
                          }
                          output={
                            "output" in part ? part.output : undefined
                          }
                        />
                      );
                    default: {
                      const p = part as Record<string, unknown>;
                      if (
                        typeof p.type === "string" &&
                        p.data &&
                        typeof p.data === "object"
                      ) {
                        if (p.type === "data-approval") {
                          const d = p.data as {
                            approvalId: string;
                            toolCallId: string;
                            toolName: string;
                            args?: Record<string, unknown>;
                            status: "pending" | "approved" | "denied";
                          };
                          if (d.approvalId) {
                            return (
                              <ApprovalCard
                                key={`${message.id}-approval-${d.approvalId}`}
                                data={d}
                                backendUrl={backendUrl}
                              />
                            );
                          }
                        }
                        if (p.type === "data-todos") {
                          const d = p.data as {
                            projectId: string;
                            todos: {
                              id: number;
                              tache: string;
                              priorite: string;
                              deadline: string | null;
                              statut: string;
                              cree_le?: string;
                              modifie_le?: string;
                            }[];
                          };
                          if (d.todos && d.todos.length > 0) {
                            return (
                              <TodoBlock
                                key={`${message.id}-todos-${i}`}
                                todos={d.todos}
                                projectId={projectId}
                                backendUrl={backendUrl}
                                onOpenViewer={() => setTodoViewerOpen(true)}
                              />
                            );
                          }
                        }
                      }
                      return null;
                    }
                  }
                })}

                <div className="absolute -bottom-4 right-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() =>
                      handleCopy(message.id, getMessageText(message.parts))
                    }
                    className="text-xs text-zinc-600 hover:text-zinc-400 flex items-center gap-1 transition-colors"
                    title="Copier la réponse"
                  >
                    {copiedId === message.id ? (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Copié
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copier
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}

          {isStreaming &&
            (messages.length === 0 ||
              messages[messages.length - 1]?.role !== "assistant") && (
              <div className="flex items-center gap-2 text-zinc-500 text-sm">
                <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-pulse" />
                <span className="animate-pulse">Réflexion…</span>
              </div>
            )}

          {error && (
            <div className="bg-red-500/5 border border-red-500/20 text-red-400 rounded-lg px-4 py-2.5 text-sm">
              Erreur : {error.message}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ═══ FIXED BOTTOM: input bar ═══ */}
      <div className="shrink-0 border-t border-zinc-800/50 bg-zinc-950 px-4 py-3">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          {pendingFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {pendingFiles.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  {f}
                </span>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            {onIngestFile && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.eml,.msg"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center justify-center w-9 h-9 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors shrink-0 mb-0.5"
                  title="Joindre un fichier"
                >
                  <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>
              </>
            )}
            <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden focus-within:border-zinc-600 transition-colors">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  if (textareaRef.current) {
                    textareaRef.current.style.height = "auto";
                    textareaRef.current.style.height =
                      Math.min(textareaRef.current.scrollHeight, 128) + "px";
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (input.trim() && !isStreaming) {
                      handleSubmit(e);
                    }
                  }
                }}
                placeholder="Écrivez votre message…"
                rows={1}
                className="w-full bg-transparent px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none resize-none max-h-32"
                disabled={isStreaming}
              />
            </div>
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="flex items-center justify-center w-9 h-9 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 disabled:text-zinc-700 disabled:hover:bg-transparent transition-colors shrink-0 mb-0.5"
              title="Envoyer"
            >
              {isStreaming ? (
                <div className="w-3.5 h-3.5 border-2 border-zinc-600 border-t-zinc-400 rounded-full animate-spin" />
              ) : (
                <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19V5m0 0l-7 7m7-7l7 7" />
                </svg>
              )}
            </button>
          </div>
        </form>
      </div>

      {viewerPath && (
        <FileViewer
          backendUrl={backendUrl}
          projectId={projectId}
          filePath={viewerPath}
          onClose={() => setViewerPath(null)}
          onNavigate={(path) => setViewerPath(path)}
        />
      )}

      {todoViewerOpen && (
        <TodoViewer
          backendUrl={backendUrl}
          projectId={projectId}
          onClose={() => setTodoViewerOpen(false)}
        />
      )}
    </div>
    </FileOpenContext.Provider>
  );
}
