import { Command } from "cmdk";
import { useEffect, useState, useMemo } from "react";
import Fuse from "fuse.js";

interface TreeEntry {
  path: string;
  name: string;
  type: "file" | "dir";
  ext?: string;
  size?: number;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  backendUrl: string;
  projectId: string;
  onOpenFile: (path: string) => void;
  onNewChat?: () => void;
  onOpenSettings?: () => void;
}

const EXT_ICONS: Record<string, string> = {
  ".pdf": "📄",
  ".docx": "📝",
  ".xlsx": "📊",
  ".xls": "📊",
  ".csv": "📊",
  ".md": "📋",
  ".txt": "📋",
  ".json": "🗂️",
  ".eml": "✉️",
  ".msg": "✉️",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function CommandPalette({
  open,
  onClose,
  backendUrl,
  projectId,
  onOpenFile,
  onNewChat,
  onOpenSettings,
}: CommandPaletteProps) {
  const [entries, setEntries] = useState<TreeEntry[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open) return;
    setSearch("");
    fetch(`${backendUrl}/api/project/${projectId}/files-tree`)
      .then((r) => r.json())
      .then((data: TreeEntry[]) => setEntries(data))
      .catch(() => setEntries([]));
  }, [open, backendUrl, projectId]);

  const dirs = useMemo(() => entries.filter((e) => e.type === "dir"), [entries]);
  const files = useMemo(() => entries.filter((e) => e.type === "file"), [entries]);

  const fuse = useMemo(
    () =>
      new Fuse(entries, {
        keys: ["name", "path"],
        threshold: 0.4,
        includeScore: true,
      }),
    [entries]
  );

  const scores = useMemo(() => {
    if (!search.trim()) return null;
    const map = new Map<string, number>();
    fuse.search(search).forEach((r) => {
      map.set(r.item.path, 1 - (r.score ?? 0));
    });
    return map;
  }, [search, fuse]);

  const openInFinder = async () => {
    const projectDir = `${backendUrl}/api/open-in-finder`;
    const res = await fetch(`${backendUrl}/api/project/${projectId}/file/.`);
    const data = await res.json();
    if (data.abs_path) {
      await fetch(projectDir, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: data.abs_path }),
      });
    }
  };

  const run = (fn?: () => void) => {
    onClose();
    fn?.();
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) onClose();
      }}
      label="Palette de commandes"
      className="fixed inset-0 z-[60]"
      filter={(value, srch) => {
        if (!srch.trim()) return 1;
        if (value.startsWith("action:")) {
          return value.toLowerCase().includes(srch.toLowerCase()) ? 1 : 0;
        }
        return scores?.get(value) ?? 0;
      }}
      loop
    >
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" cmdk-overlay="" />
      <div className="fixed inset-0 flex items-start justify-center pt-[15vh] pointer-events-none">
        <div className="w-full max-w-lg bg-zinc-900 border border-zinc-700/60 rounded-xl shadow-2xl overflow-hidden pointer-events-auto">
          <div className="flex items-center gap-2 px-4 border-b border-zinc-800">
            <svg
              className="w-4 h-4 text-zinc-500 shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Rechercher fichiers, dossiers, actions…"
              className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 py-3 outline-none"
            />
            <kbd className="text-[10px] text-zinc-600 bg-zinc-800 px-1.5 py-0.5 rounded font-mono">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-[50vh] overflow-y-auto p-2 fileviewer-scroll">
            <Command.Empty className="text-sm text-zinc-600 text-center py-8">
              Aucun résultat
            </Command.Empty>

            {/* Dossiers */}
            {dirs.length > 0 && (
              <Command.Group heading="Dossiers" className="mb-2">
                {dirs.map((dir) => (
                  <Command.Item
                    key={`dir:${dir.path}`}
                    value={dir.path}
                    onSelect={() => {
                      onOpenFile(dir.path);
                      onClose();
                    }}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors data-[selected=true]:bg-zinc-800 hover:bg-zinc-800/60"
                  >
                    <svg
                      className="w-4 h-4 text-zinc-500 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                      />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <div className="text-zinc-200 truncate">{dir.name}/</div>
                      {dir.path !== dir.name && (
                        <div className="text-[11px] text-zinc-600 truncate">
                          {dir.path}
                        </div>
                      )}
                    </div>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Fichiers */}
            <Command.Group heading="Fichiers" className="mb-2">
              {files.map((file) => (
                <Command.Item
                  key={`file:${file.path}`}
                  value={file.path}
                  onSelect={() => {
                    onOpenFile(file.path);
                    onClose();
                  }}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors data-[selected=true]:bg-zinc-800 hover:bg-zinc-800/60"
                >
                  <span className="text-base shrink-0">
                    {EXT_ICONS[file.ext || ""] || "📎"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-zinc-200 truncate">{file.name}</div>
                    {file.path !== file.name && (
                      <div className="text-[11px] text-zinc-600 truncate">
                        {file.path}
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-zinc-600 shrink-0">
                    {file.size != null && formatSize(file.size)}
                  </span>
                </Command.Item>
              ))}
            </Command.Group>

            {/* Actions rapides */}
            <Command.Group heading="Actions" className="mb-1">
              <Command.Item
                value="action:nouvelle conversation chat"
                keywords={["nouveau", "chat", "conversation", "reset"]}
                onSelect={() => run(onNewChat)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors data-[selected=true]:bg-zinc-800 hover:bg-zinc-800/60"
              >
                <svg className="w-4 h-4 text-zinc-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span className="text-zinc-200">Nouvelle conversation</span>
              </Command.Item>

              <Command.Item
                value="action:parametres reglages settings"
                keywords={["paramètres", "réglages", "config", "settings", "profil"]}
                onSelect={() => run(onOpenSettings)}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors data-[selected=true]:bg-zinc-800 hover:bg-zinc-800/60"
              >
                <svg className="w-4 h-4 text-zinc-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span className="text-zinc-200">Paramètres</span>
              </Command.Item>

              <Command.Item
                value="action:ouvrir finder dossier projet"
                keywords={["finder", "explorer", "dossier", "ouvrir", "bureau"]}
                onSelect={() => {
                  onClose();
                  openInFinder();
                }}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors data-[selected=true]:bg-zinc-800 hover:bg-zinc-800/60"
              >
                <svg className="w-4 h-4 text-zinc-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                <span className="text-zinc-200">Ouvrir dans le Finder</span>
              </Command.Item>
            </Command.Group>
          </Command.List>

          <div className="border-t border-zinc-800 px-4 py-2 flex items-center justify-between text-[11px] text-zinc-600">
            <span>
              {entries.length} élément{entries.length > 1 ? "s" : ""}
            </span>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1">
                <kbd className="bg-zinc-800 px-1 rounded font-mono">↑↓</kbd>
                naviguer
              </span>
              <span className="flex items-center gap-1">
                <kbd className="bg-zinc-800 px-1 rounded font-mono">↵</kbd>
                ouvrir
              </span>
            </div>
          </div>
        </div>
      </div>
    </Command.Dialog>
  );
}
