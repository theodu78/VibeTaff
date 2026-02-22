import { useState, useEffect, useCallback, useRef } from "react";
import Markdown from "./Markdown";
import DocumentEditor from "./DocumentEditor";

interface FileViewerProps {
  backendUrl: string;
  projectId: string;
  filePath: string;
  onClose: () => void;
  onNavigate: (path: string) => void;
}

interface FileData {
  type: "file";
  path: string;
  abs_path?: string;
  name: string;
  extension: string;
  content: string;
  metadata?: Record<string, unknown>;
}

interface DirData {
  type: "directory";
  path: string;
  entries: { name: string; is_dir: boolean; size: number | null }[];
}

function formatSize(bytes: number | null): string {
  if (bytes === null) return "";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function FileViewer({
  backendUrl,
  projectId,
  filePath,
  onClose,
  onNavigate,
}: FileViewerProps) {
  const [data, setData] = useState<FileData | DirData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  const fetchFile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${backendUrl}/api/project/${projectId}/file/${encodeURIComponent(filePath)}`
      );
      const json = await res.json();
      if (json.status === "error") {
        setError(json.message);
      } else {
        setData(json);
      }
    } catch {
      setError("Erreur réseau");
    }
    setLoading(false);
  }, [backendUrl, projectId, filePath]);

  useEffect(() => {
    fetchFile();
  }, [fetchFile]);

  useEffect(() => {
    if (contentRef.current) contentRef.current.scrollTop = 0;
  }, [data, editing]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-3xl h-[85vh] mx-4 bg-zinc-900 border border-zinc-700/50 rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <div className="flex items-center gap-2 min-w-0">
            {filePath !== "." && (
              <button
                onClick={() => {
                  const parent = filePath.includes("/")
                    ? filePath.split("/").slice(0, -1).join("/")
                    : ".";
                  onNavigate(parent);
                }}
                className="text-zinc-500 hover:text-zinc-300 transition-colors shrink-0"
                title="Dossier parent"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            )}
            <span className="text-sm text-zinc-300 truncate font-medium">
              {filePath === "." ? "Fichiers du projet" : filePath}
            </span>
          </div>
          <div className="flex items-center gap-1 ml-auto shrink-0">
            {data?.type === "file" && data.extension === ".md" && (
              <button
                onClick={() => setEditing((e) => !e)}
                className={`transition-colors px-2 py-1 rounded text-xs font-medium flex items-center gap-1 ${
                  editing
                    ? "text-zinc-200 bg-zinc-700"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                }`}
                title={editing ? "Mode lecture" : "Mode édition"}
              >
                {editing ? (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    Lecture
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Éditer
                  </>
                )}
              </button>
            )}
            {data?.type === "file" && data.abs_path && [".pdf", ".docx", ".xlsx", ".xls"].includes(data.extension) && (
              <button
                onClick={async () => {
                  await fetch(`${backendUrl}/api/open-file`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ path: data.abs_path }),
                  });
                }}
                className="text-emerald-500 hover:text-emerald-300 transition-colors px-2 py-1 rounded hover:bg-zinc-800 text-xs font-medium flex items-center gap-1"
                title="Ouvrir avec l'application par défaut"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Aperçu
              </button>
            )}
            {data && "abs_path" in data && (
              <button
                onClick={async () => {
                  await fetch(`${backendUrl}/api/open-in-finder`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ path: (data as { abs_path: string }).abs_path }),
                  });
                }}
                className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-800"
                title="Ouvrir dans le Finder"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </button>
            )}
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-800"
            title="Fermer (Esc)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          </div>
        </div>

        {/* Content */}
        <div
          ref={contentRef}
          className="flex-1 min-h-0 overflow-y-auto p-4 fileviewer-scroll"
        >
          {loading && (
            <div className="flex items-center gap-2 text-zinc-500 text-sm">
              <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-pulse" />
              Chargement…
            </div>
          )}

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          {data?.type === "directory" && (
            <div className="space-y-0.5">
              {data.entries.length === 0 && (
                <p className="text-zinc-500 text-sm">Dossier vide</p>
              )}
              {data.entries.map((entry) => (
                <button
                  key={entry.name}
                  onClick={() => {
                    const newPath =
                      data.path === "." || data.path === ""
                        ? entry.name
                        : `${data.path}/${entry.name}`;
                    onNavigate(newPath);
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm hover:bg-zinc-800 transition-colors text-left"
                >
                  {entry.is_dir ? (
                    <svg className="w-4 h-4 text-zinc-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-zinc-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  )}
                  <span className="text-zinc-200 truncate">{entry.name}</span>
                  {entry.size !== null && (
                    <span className="text-zinc-600 text-xs ml-auto shrink-0">
                      {formatSize(entry.size)}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {data?.type === "file" && !editing && (
            <>
              {data.extension === ".md" ? (
                <Markdown>{data.content}</Markdown>
              ) : data.extension === ".json" ? (
                <pre className="text-xs text-zinc-300 bg-zinc-800/50 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap font-mono">
                  {data.content}
                </pre>
              ) : (
                <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-mono">
                  {data.content}
                </pre>
              )}
            </>
          )}

          {editing && data?.type === "file" && data.extension === ".md" && (
            <DocumentEditor
              content={data.content}
              fileName={data.name}
              onSave={async (md) => {
                await fetch(
                  `${backendUrl}/api/project/${projectId}/file/${encodeURIComponent(filePath)}`,
                  {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ content: md }),
                  }
                );
                setData({ ...data, content: md });
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
