import DataGrid from "./DataGrid";
import EmailDraft from "./EmailDraft";

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
  query_project_memory: "Recherche dans les documents",
  save_to_long_term_memory: "Mémorisation",
  web_search: "Recherche web",
  draft_email: "Brouillon d'email",
  run_local_calculation: "Calcul en cours",
};

const TOOL_ICONS: Record<string, string> = {
  list_project_files: "📁",
  read_file_content: "📄",
  write_project_note: "✏️",
  write_json_table: "🧮",
  query_project_memory: "🔍",
  save_to_long_term_memory: "🧠",
  web_search: "🌐",
  draft_email: "📧",
  run_local_calculation: "🔢",
};

function tryParseEmailDraft(output: unknown): {
  to: string;
  subject: string;
  body: string;
  mailto_link: string;
} | null {
  try {
    const data = typeof output === "string" ? JSON.parse(output) : output;
    if (data?.type === "email_draft" && data.to && data.subject && data.body) {
      return data;
    }
  } catch {
    // not an email draft
  }
  return null;
}

function tryParseJsonTable(input: Record<string, unknown> | undefined): {
  data: Record<string, unknown>[];
  name: string;
} | null {
  if (!input) return null;
  const jsonData = input.json_data;
  const tableName = input.table_name;
  if (Array.isArray(jsonData) && jsonData.length > 0) {
    return { data: jsonData as Record<string, unknown>[], name: String(tableName || "") };
  }
  return null;
}

export default function ToolCall({ toolName, state, input, output }: ToolCallProps) {
  const label = TOOL_LABELS[toolName] || toolName;
  const icon = TOOL_ICONS[toolName] || "🔧";
  const isLoading = state === "input-streaming" || state === "input-available";
  const isDone = state === "output-available";

  if (isDone && toolName === "draft_email") {
    const emailData = tryParseEmailDraft(output);
    if (emailData) {
      return (
        <EmailDraft
          to={emailData.to}
          subject={emailData.subject}
          body={emailData.body}
          mailtoLink={emailData.mailto_link}
        />
      );
    }
  }

  if (isDone && toolName === "write_json_table") {
    const tableData = tryParseJsonTable(input);
    if (tableData) {
      return <DataGrid data={tableData.data} tableName={tableData.name} />;
    }
  }

  if (isDone && toolName === "run_local_calculation") {
    const code = typeof input?.python_code === "string" ? input.python_code : "";
    return (
      <div className="my-2 rounded-lg border border-zinc-700 bg-zinc-900/50 overflow-hidden text-xs">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800">
          <span>🔢</span>
          <span className="font-medium text-zinc-300">Calcul</span>
          <span className="ml-auto text-zinc-500">terminé</span>
        </div>
        {code && (
          <div className="px-3 py-2 border-b border-zinc-800">
            <pre className="text-zinc-500 whitespace-pre-wrap break-all font-mono text-[11px] max-h-28 overflow-y-auto">
              {code}
            </pre>
          </div>
        )}
        <div className="px-3 py-2 bg-zinc-800/30">
          <pre className="text-zinc-300 whitespace-pre-wrap break-all font-mono">
            {typeof output === "string" ? output : JSON.stringify(output)}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="my-2 rounded-lg border border-zinc-700/40 bg-zinc-800/30 overflow-hidden text-xs">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-700/30">
        <span>{icon}</span>
        <span className="font-medium text-zinc-400">{label}</span>
        {isLoading && (
          <span className="ml-auto text-zinc-500 animate-pulse">
            en cours...
          </span>
        )}
        {isDone && <span className="ml-auto text-zinc-600">terminé</span>}
      </div>

      {input && Object.keys(input).length > 0 && !isDone && (
        <div className="px-3 py-2 border-b border-zinc-800">
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
