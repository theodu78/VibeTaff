import { useState, useCallback } from "react";

function summarizeArgs(args?: Record<string, unknown>): string {
  if (!args) return "";
  const vals = Object.values(args)
    .filter((v) => typeof v === "string" && v.length > 0)
    .map((v) => String(v));
  if (vals.length === 0) return "";
  return vals.join(" → ");
}

const ACTION_DESCRIPTIONS: Record<string, (args?: Record<string, unknown>) => string> = {
  write_project_note: (args) =>
    `Créer le fichier « ${args?.title || args?.file_name || "sans titre"}.md »`,
  draft_email: (args) =>
    `Rédiger un email à ${args?.to || "?"} : « ${args?.subject || "sans objet"} »`,
  delete_project_file: (args) =>
    `Supprimer « ${args?.file_name || summarizeArgs(args) || "fichier"} »`,
  rename_project_file: (args) =>
    `Déplacer « ${args?.old_name || "?"} » → « ${args?.new_name || "?"} »`,
  save_meeting_note: (args) =>
    `Créer le compte-rendu « ${args?.titre || "réunion"} »`,
  export_to_pdf: (args) =>
    `Exporter « ${args?.file_name || "fichier"} » en PDF`,
};

interface ApprovalData {
  approvalId: string;
  toolCallId: string;
  toolName: string;
  args?: Record<string, unknown>;
  status: "pending" | "approved" | "denied";
}

interface ApprovalCardProps {
  data: ApprovalData;
  backendUrl: string;
}

export default function ApprovalCard({ data, backendUrl }: ApprovalCardProps) {
  const [responded, setResponded] = useState(false);
  const [localStatus, setLocalStatus] = useState(data.status);

  const displayStatus = localStatus !== "pending" ? localStatus : data.status;
  const isPending = displayStatus === "pending" && !responded;

  const respond = useCallback(
    async (approved: boolean) => {
      setResponded(true);
      setLocalStatus(approved ? "approved" : "denied");
      try {
        await fetch(`${backendUrl}/api/tool-approval/${data.approvalId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved }),
        });
      } catch { /* */ }
    },
    [backendUrl, data.approvalId]
  );

  const descFn = ACTION_DESCRIPTIONS[data.toolName];
  const description = descFn
    ? descFn(data.args)
    : `${data.toolName}${data.args ? ` (${summarizeArgs(data.args)})` : ""}`;

  if (!isPending) {
    const isApproved = displayStatus === "approved";
    return (
      <div className="my-2 flex items-center gap-2 text-xs text-zinc-500">
        <span className={isApproved ? "text-emerald-500" : "text-zinc-500"}>
          {isApproved ? "✓" : "✗"}
        </span>
        <span>
          {description} — {isApproved ? "approuvé" : "refusé"}
        </span>
      </div>
    );
  }

  return (
    <div className="my-3 rounded-lg border border-zinc-700/50 bg-zinc-800/30 overflow-hidden text-sm">
      <div className="px-4 py-3">
        <p className="text-zinc-200 mb-3">{description}</p>
        <div className="flex gap-2">
          <button
            onClick={() => respond(true)}
            className="flex-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
          >
            Approuver
          </button>
          <button
            onClick={() => respond(false)}
            className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors border border-zinc-700"
          >
            Refuser
          </button>
        </div>
      </div>
    </div>
  );
}
