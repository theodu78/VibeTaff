import { useState, useEffect, useCallback } from "react";
import type { TodoItem } from "./TodoBlock";

interface TodoViewerProps {
  backendUrl: string;
  projectId: string;
  onClose: () => void;
}

const PRIORITY_LABELS: Record<string, { label: string; color: string }> = {
  haute: { label: "Haute", color: "text-red-400" },
  normale: { label: "Normale", color: "text-zinc-400" },
  basse: { label: "Basse", color: "text-emerald-400" },
};


export default function TodoViewer({
  backendUrl,
  projectId,
  onClose,
}: TodoViewerProps) {
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "active" | "done">("all");

  const fetchTodos = useCallback(async () => {
    try {
      const res = await fetch(
        `${backendUrl}/api/project/${projectId}/todos`
      );
      if (res.ok) {
        const data = await res.json();
        setTodos(data.todos || []);
      }
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [backendUrl, projectId]);

  useEffect(() => {
    fetchTodos();
  }, [fetchTodos]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const updateTodo = useCallback(
    async (taskId: number, updates: Partial<TodoItem>) => {
      setTodos((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, ...updates } : t))
      );
      try {
        await fetch(
          `${backendUrl}/api/project/${projectId}/todos/${taskId}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updates),
          }
        );
      } catch {
        fetchTodos();
      }
    },
    [backendUrl, projectId, fetchTodos]
  );

  const deleteTodo = useCallback(
    async (taskId: number) => {
      setTodos((prev) => prev.filter((t) => t.id !== taskId));
      try {
        await fetch(
          `${backendUrl}/api/project/${projectId}/todos/${taskId}`,
          { method: "DELETE" }
        );
      } catch {
        fetchTodos();
      }
    },
    [backendUrl, projectId, fetchTodos]
  );

  const toggleStatus = (todo: TodoItem) => {
    const newStatut = todo.statut === "fait" ? "a_faire" : "fait";
    updateTodo(todo.id, { statut: newStatut });
  };

  const cyclePriority = (todo: TodoItem) => {
    const cycle = ["basse", "normale", "haute"];
    const idx = cycle.indexOf(todo.priorite);
    const next = cycle[(idx + 1) % cycle.length];
    updateTodo(todo.id, { priorite: next });
  };

  const filtered = todos.filter((t) => {
    if (filter === "active")
      return t.statut === "a_faire" || t.statut === "en_cours";
    if (filter === "done")
      return t.statut === "fait" || t.statut === "annule";
    return true;
  });

  const doneCount = todos.filter(
    (t) => t.statut === "fait" || t.statut === "annule"
  ).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg max-h-[80vh] mx-4 bg-zinc-900 border border-zinc-700/50 rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <svg
              className="w-4 h-4 text-zinc-500"
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
            <span className="text-sm font-medium text-zinc-200">
              To-dos
            </span>
            <span className="text-xs text-zinc-500">
              {doneCount}/{todos.length}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-800"
            title="Fermer (Esc)"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Filters */}
        <div className="shrink-0 flex gap-1 px-4 py-2 border-b border-zinc-800/50">
          {(["all", "active", "done"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                filter === f
                  ? "bg-zinc-700 text-zinc-200"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              {f === "all" ? "Toutes" : f === "active" ? "En cours" : "Terminées"}
            </button>
          ))}
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-5 h-5 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 text-sm text-zinc-600">
              {filter === "all"
                ? "Aucune tâche. Demandez à l'agent d'en créer."
                : "Aucune tâche dans ce filtre."}
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/40">
              {filtered.map((todo) => {
                const isDone =
                  todo.statut === "fait" || todo.statut === "annule";
                const prio = PRIORITY_LABELS[todo.priorite] || PRIORITY_LABELS.normale;

                return (
                  <div
                    key={todo.id}
                    className="flex items-start gap-3 px-4 py-3 hover:bg-zinc-800/20 transition-colors group"
                  >
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleStatus(todo)}
                      className="shrink-0 mt-0.5"
                      title={isDone ? "Marquer comme à faire" : "Marquer comme fait"}
                    >
                      {isDone ? (
                        <svg
                          className="w-4 h-4 text-zinc-600 hover:text-zinc-400 transition-colors"
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
                        <div className="w-4 h-4 rounded-full border border-zinc-600 hover:border-zinc-400 transition-colors" />
                      )}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm leading-relaxed ${
                          isDone
                            ? "text-zinc-600 line-through"
                            : "text-zinc-200"
                        }`}
                      >
                        {todo.tache}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <button
                          onClick={() => cyclePriority(todo)}
                          className={`text-xs ${prio.color} hover:opacity-80 transition-opacity`}
                          title="Changer la priorité"
                        >
                          {prio.label}
                        </button>
                        {todo.deadline && (
                          <span className="text-xs text-zinc-600">
                            {todo.deadline}
                          </span>
                        )}
                        <span className="text-xs text-zinc-700">
                          #{todo.id}
                        </span>
                      </div>
                    </div>

                    {/* Delete */}
                    <button
                      onClick={() => deleteTodo(todo.id)}
                      className="shrink-0 opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-red-400 transition-all p-0.5"
                      title="Supprimer"
                    >
                      <svg
                        className="w-3.5 h-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
