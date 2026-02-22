import { useState, useRef, useEffect } from "react";

interface ThinkingBlockProps {
  text: string;
  isStreaming: boolean;
}

const COLLAPSED_HEIGHT = 130;
const MAX_EXPANDED_HEIGHT = 400;

export default function ThinkingBlock({ text, isStreaming }: ThinkingBlockProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const userToggledRef = useRef(false);
  const prevStreamingRef = useRef(isStreaming);
  const contentRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (isStreaming && startTimeRef.current === null) {
      startTimeRef.current = Date.now();
    }
    if (!isStreaming) {
      startTimeRef.current = null;
    }
  }, [isStreaming]);

  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(() => {
      if (startTimeRef.current) {
        setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [isStreaming]);

  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && !userToggledRef.current) {
      setCollapsed(true);
      setExpanded(false);
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming]);

  useEffect(() => {
    if (isStreaming && contentRef.current && !expanded) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [text, isStreaming, expanded]);

  if (!text && !isStreaming) return null;

  const preview = text
    ? text.slice(0, 80).replace(/\n/g, " ") + (text.length > 80 ? "…" : "")
    : "";

  const handleToggle = () => {
    userToggledRef.current = true;
    if (collapsed) {
      setCollapsed(false);
    } else if (expanded) {
      setExpanded(false);
    } else {
      setCollapsed(true);
      setExpanded(false);
    }
  };

  const handleExpand = () => {
    userToggledRef.current = true;
    setExpanded(true);
  };

  if (collapsed) {
    return (
      <div className="mb-3">
        <button
          onClick={handleToggle}
          className="flex items-center gap-1.5 text-[13px] text-zinc-600 hover:text-zinc-400 transition-colors"
        >
          <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="shrink-0">Réflexion</span>
          {preview && (
            <span className="text-zinc-700 truncate max-w-md font-normal">— {preview}</span>
          )}
        </button>
      </div>
    );
  }

  const needsClamp = !expanded && (isStreaming || text.length > 400);

  return (
    <div className="mb-3">
      <button
        onClick={handleToggle}
        className="flex items-center gap-1.5 text-[13px] text-zinc-600 hover:text-zinc-400 transition-colors mb-1.5"
      >
        <svg className="w-3 h-3 shrink-0 rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="shrink-0">
          {isStreaming ? "Réflexion en cours…" : "Réflexion"}
        </span>
        {isStreaming && elapsed > 0 && (
          <span className="text-zinc-700 text-[11px] ml-1">{elapsed}s</span>
        )}
      </button>

      <div className="relative pl-4 border-l border-zinc-800">
        <div
          ref={contentRef}
          className={`transition-all duration-200 ${
            expanded ? "overflow-y-auto" : "overflow-hidden"
          }`}
          style={{
            maxHeight: expanded
              ? `${MAX_EXPANDED_HEIGHT}px`
              : needsClamp
              ? `${COLLAPSED_HEIGHT}px`
              : "none",
          }}
        >
          <p
            className="text-[13px] leading-relaxed text-zinc-400 whitespace-pre-wrap break-words"
            style={{ opacity: isStreaming ? 0.7 : 0.55 }}
          >
            {text}
            {isStreaming && (
              <span className="inline-block w-1.5 h-3.5 bg-zinc-500 ml-0.5 animate-pulse align-text-bottom rounded-sm" />
            )}
          </p>
        </div>

        {needsClamp && (
          <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-zinc-950/80 to-transparent pointer-events-none" />
        )}

        {needsClamp && !isStreaming && (
          <button
            onClick={handleExpand}
            className="mt-1 text-xs text-zinc-600 hover:text-zinc-400 transition-colors relative z-10"
          >
            Voir tout
          </button>
        )}
      </div>
    </div>
  );
}
