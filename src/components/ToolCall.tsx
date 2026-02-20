interface ToolCallProps {
  toolName: string;
  state: string;
  input?: Record<string, unknown>;
  output?: unknown;
}

const TOOL_LABELS: Record<string, string> = {
  list_project_files: "Exploration des fichiers",
  read_file_content: "Lecture d'un fichier",
  write_project_note: "Écriture d'une note",
  write_json_table: "Création d'un tableau",
};

const TOOL_ICONS: Record<string, string> = {
  list_project_files: "📁",
  read_file_content: "📄",
  write_project_note: "✏️",
  write_json_table: "🧮",
};

export default function ToolCall({
  toolName,
  state,
  input,
  output,
}: ToolCallProps) {
  const label = TOOL_LABELS[toolName] || toolName;
  const icon = TOOL_ICONS[toolName] || "🔧";
  const isLoading =
    state === "input-streaming" || state === "input-available";
  const isDone = state === "output-available";

  return (
    <div className="my-2 rounded-lg border border-zinc-700 bg-zinc-900/50 overflow-hidden text-xs">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800">
        <span>{icon}</span>
        <span className="font-medium text-zinc-300">{label}</span>
        {isLoading && (
          <span className="ml-auto text-amber-400 animate-pulse">
            en cours...
          </span>
        )}
        {isDone && <span className="ml-auto text-emerald-400">terminé</span>}
      </div>

      {input && Object.keys(input).length > 0 && (
        <div className="px-3 py-2 border-b border-zinc-800">
          <div className="text-zinc-500 mb-1">Paramètres :</div>
          <pre className="text-zinc-400 whitespace-pre-wrap break-all">
            {Object.entries(input)
              .map(([k, v]) => {
                const val =
                  typeof v === "string"
                    ? v.length > 100
                      ? v.slice(0, 100) + "..."
                      : v
                    : JSON.stringify(v);
                return `${k}: ${val}`;
              })
              .join("\n")}
          </pre>
        </div>
      )}

      {isDone && output != null && (
        <div className="px-3 py-2">
          <div className="text-zinc-500 mb-1">Résultat :</div>
          <pre className="text-zinc-400 whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
            {typeof output === "string"
              ? output.length > 500
                ? output.slice(0, 500) + "\n..."
                : output
              : JSON.stringify(output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
