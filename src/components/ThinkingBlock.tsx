import { useState, useRef, useEffect } from "react";

interface ThinkingBlockProps {
  text: string;
  isStreaming: boolean;
}

const MAX_VISIBLE_LINES = 8;

export default function ThinkingBlock({ text, isStreaming }: ThinkingBlockProps) {
  const [collapsed, setCollapsed] = useState(false);
  const userToggledRef = useRef(false);
  const prevStreamingRef = useRef(isStreaming);

  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && !userToggledRef.current) {
      setCollapsed(true);
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming]);

  if (!text && !isStreaming) return null;

  const lines = text
    ? text.split("\n").filter((l) => l.trim().length > 0)
    : [];

  const handleToggle = () => {
    userToggledRef.current = true;
    setCollapsed((c) => !c);
  };

  const preview =
    lines.length > 0
      ? lines[0].slice(0, 80) +
        (lines[0].length > 80 || lines.length > 1 ? "…" : "")
      : "";

  if (collapsed) {
    return (
      <div className="mb-3">
        <button
          onClick={handleToggle}
          className="flex items-center gap-1.5 text-[13px] text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          <svg
            className="w-3 h-3 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="shrink-0">Réflexion</span>
          {preview && (
            <span className="text-zinc-700 truncate max-w-md font-normal">
              — {preview}
            </span>
          )}
        </button>
      </div>
    );
  }

  const isOverflowing = isStreaming && lines.length > MAX_VISIBLE_LINES;
  const visibleLines = isStreaming
    ? lines.slice(-MAX_VISIBLE_LINES)
    : lines;

  return (
    <div className="mb-3">
      <button
        onClick={handleToggle}
        className="flex items-center gap-1.5 text-[13px] text-zinc-600 hover:text-zinc-400 transition-colors mb-1.5"
      >
        <svg
          className="w-3 h-3 shrink-0 rotate-90"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="shrink-0">
          {isStreaming ? "Réflexion en cours…" : "Réflexion"}
        </span>
      </button>
      <div className="relative pl-4 border-l border-zinc-800">
        {isOverflowing && (
          <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-zinc-950 to-transparent z-10 pointer-events-none" />
        )}
        {visibleLines.map((line, i) => {
          const isLast = i === visibleLines.length - 1 && isStreaming;
          return (
            <p
              key={i}
              className={`text-[13px] leading-relaxed text-zinc-500 ${
                isLast ? "animate-pulse" : ""
              }`}
              style={{ opacity: isStreaming ? (isLast ? 0.6 : 0.45) : 0.4 }}
            >
              {line}
            </p>
          );
        })}
        {isStreaming && visibleLines.length === 0 && (
          <p className="text-[13px] text-zinc-600 animate-pulse">…</p>
        )}
      </div>
    </div>
  );
}
