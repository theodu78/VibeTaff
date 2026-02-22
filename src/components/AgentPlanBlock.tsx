interface PlanItem {
  id: string;
  content: string;
  status: "pending" | "in_progress" | "completed";
}

interface AgentPlanBlockProps {
  todos: PlanItem[];
}

export type { PlanItem };

export default function AgentPlanBlock({ todos }: AgentPlanBlockProps) {
  const done = todos.filter((t) => t.status === "completed").length;
  const total = todos.length;
  const allDone = done === total;

  return (
    <div className="my-3 rounded-lg border border-zinc-700/40 bg-zinc-800/30 overflow-hidden">
      <div className="flex items-center gap-2.5 px-4 py-2.5">
        {allDone ? (
          <svg
            className="w-4 h-4 text-emerald-500 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        ) : (
          <svg
            className="w-4 h-4 text-zinc-500 shrink-0 animate-spin-slow"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        )}
        <span className="text-sm text-zinc-300 font-medium">
          {allDone ? "Plan terminé" : "Plan de travail"}
        </span>
        <span className="text-xs text-zinc-500 ml-auto">
          {done}/{total}
        </span>
      </div>

      <div className="border-t border-zinc-800/50">
        {todos.map((item) => (
          <div
            key={item.id}
            className="flex items-start gap-2.5 px-4 py-2 text-left"
          >
            {item.status === "completed" ? (
              <svg
                className="w-4 h-4 text-emerald-500/70 shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            ) : item.status === "in_progress" ? (
              <div className="w-4 h-4 shrink-0 mt-0.5 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              </div>
            ) : (
              <div className="w-4 h-4 rounded-full border border-zinc-600 shrink-0 mt-0.5" />
            )}
            <span
              className={`text-sm leading-relaxed ${
                item.status === "completed"
                  ? "text-zinc-600 line-through"
                  : item.status === "in_progress"
                  ? "text-zinc-200"
                  : "text-zinc-400"
              }`}
            >
              {item.content}
            </span>
          </div>
        ))}
      </div>

      {!allDone && (
        <div className="px-4 pb-2">
          <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-amber-500/60 to-amber-400/80 rounded-full transition-all duration-500"
              style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
