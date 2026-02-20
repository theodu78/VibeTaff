import { useState, useCallback } from "react";

interface TodoItem {
  id: number;
  tache: string;
  priorite: string;
  deadline: string | null;
  statut: string;
  cree_le?: string;
  modifie_le?: string;
}

interface TodoBlockProps {
  todos: TodoItem[];
  projectId: string;
  backendUrl: string;
  onOpenViewer?: () => void;
}

export type { TodoItem };

export default function TodoBlock({
  todos: initialTodos,
  projectId,
  backendUrl,
  onOpenViewer,
}: TodoBlockProps) {
  const [todos, setTodos] = useState<TodoItem[]>(initialTodos);

  const toggleTodo = useCallback(
    async (taskId: number, currentStatut: string) => {
      const newStatut = currentStatut === "fait" ? "a_faire" : "fait";
      setTodos((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, statut: newStatut } : t))
      );
      try {
        await fetch(
          `${backendUrl}/api/project/${projectId}/todos/${taskId}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ statut: newStatut }),
          }
        );
      } catch {
        setTodos((prev) =>
          prev.map((t) =>
            t.id === taskId ? { ...t, statut: currentStatut } : t
          )
        );
      }
    },
    [backendUrl, projectId]
  );

  const doneCount = todos.filter((t) => t.statut === "fait" || t.statut === "annule").length;
  const total = todos.length;

  return (
    <div className="my-3 rounded-lg border border-zinc-700/40 bg-zinc-800/30 overflow-hidden">
      <button
        onClick={onOpenViewer}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 hover:bg-zinc-700/20 transition-colors cursor-pointer"
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
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <span className="text-sm text-zinc-300 font-medium">To-dos</span>
        <span className="text-sm text-zinc-500">{total}</span>
        {doneCount > 0 && (
          <span className="text-xs text-zinc-600 ml-auto">
            {doneCount}/{total} terminée{doneCount > 1 ? "s" : ""}
          </span>
        )}
      </button>

      <div className="border-t border-zinc-800/50">
        {todos.map((todo) => {
          const isDone = todo.statut === "fait" || todo.statut === "annule";
          return (
            <button
              key={todo.id}
              onClick={() => toggleTodo(todo.id, todo.statut)}
              className="w-full flex items-start gap-2.5 px-4 py-2 hover:bg-zinc-700/15 transition-colors text-left group"
            >
              {isDone ? (
                <svg
                  className="w-4 h-4 text-zinc-600 shrink-0 mt-0.5"
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
                <div className="w-4 h-4 rounded-full border border-zinc-600 group-hover:border-zinc-400 shrink-0 mt-0.5 transition-colors" />
              )}
              <span
                className={`text-sm leading-relaxed ${
                  isDone
                    ? "text-zinc-600 line-through"
                    : "text-zinc-300"
                }`}
              >
                {todo.tache}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
