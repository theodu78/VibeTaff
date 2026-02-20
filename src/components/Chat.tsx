import { useRef, useEffect, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import ToolCall from "./ToolCall";

interface ChatProps {
  backendUrl: string;
}

export default function Chat({ backendUrl }: ChatProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { messages, sendMessage, status, error } = useChat({
    transport: new DefaultChatTransport({
      api: `${backendUrl}/api/chat`,
    }),
  });

  const isStreaming = status === "streaming";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage({ text: input });
    setInput("");
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full min-h-[50vh] text-center">
              <h2 className="text-2xl font-bold text-zinc-100 mb-2">
                Bienvenue sur Vibetaff
              </h2>
              <p className="text-zinc-500 max-w-md">
                Posez une question ou décrivez ce que vous voulez accomplir.
                L'agent IA vous assistera.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-zinc-800 text-zinc-100"
                }`}
              >
                {message.parts.map((part, i) => {
                  switch (part.type) {
                    case "text":
                      return (
                        <div
                          key={`${message.id}-${i}`}
                          className="whitespace-pre-wrap text-sm leading-relaxed"
                        >
                          {part.text}
                        </div>
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
                    default:
                      return null;
                  }
                })}
              </div>
            </div>
          ))}

          {isStreaming &&
            (messages.length === 0 ||
              messages[messages.length - 1]?.role !== "assistant") && (
              <div className="flex justify-start">
                <div className="bg-zinc-800 rounded-2xl px-4 py-3">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <div className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" />
                  </div>
                </div>
              </div>
            )}

          {error && (
            <div className="flex justify-center">
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-2 text-sm">
                Erreur : {error.message}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-zinc-800 bg-zinc-950 px-4 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Écrivez votre message..."
              className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
              disabled={isStreaming}
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl px-5 py-3 text-sm font-medium transition-colors"
            >
              {isStreaming ? "..." : "Envoyer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
