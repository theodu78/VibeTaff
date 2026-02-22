import { useState, useEffect, useCallback } from "react";

const BACKEND = "http://localhost:11434";

interface SettingsData {
  profile: string;
  "llm.provider": string;
  "llm.model": string;
  "security.allow_code_execution": boolean;
  "security.sandbox_mode": string;
  "security.approval_all_tools": boolean;
  "security.log_export_url": string | null;
  "tools.dynamic_injection": boolean;
  "tools.disabled_tools": string[];
  "tools.disabled_categories": string[];
  "ui.show_thinking": boolean;
  "ui.language": string;
  [key: string]: unknown;
}

interface ProviderInfo {
  id: string;
  name: string;
  models: string[];
  configured: boolean;
  supports_thinking: boolean;
}

interface SettingsProps {
  onDone: () => void;
  isFirstTime: boolean;
}

const ALL_TOOLS = [
  { name: "run_local_calculation", label: "Calcul Python", category: "compute" },
  { name: "web_search", label: "Recherche web", category: "web" },
  { name: "draft_email", label: "Brouillon email", category: "web" },
  { name: "delete_project_file", label: "Supprimer fichier", category: "files" },
  { name: "rename_project_file", label: "Renommer fichier", category: "files" },
  { name: "export_to_pdf", label: "Export PDF", category: "files" },
];

export default function Settings({ onDone, isFirstTime }: SettingsProps) {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "security" | "tools">("general");

  useEffect(() => {
    fetch(`${BACKEND}/api/settings`).then(r => r.json()).then(setSettings).catch(() => {});
    fetch(`${BACKEND}/api/providers`).then(r => r.json()).then(d => setProviders(d.providers || [])).catch(() => {});
  }, []);

  const update = useCallback((key: string, value: unknown) => {
    setSettings(prev => prev ? { ...prev, [key]: value } : prev);
  }, []);

  const save = useCallback(async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const res = await fetch(`${BACKEND}/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      const data = await res.json();
      setSettings(data);
    } catch { /* ignore */ }
    setSaving(false);
  }, [settings]);

  const applyProfile = useCallback(async (profile: string) => {
    try {
      const res = await fetch(`${BACKEND}/api/settings/profile/${profile}`, { method: "PUT" });
      const data = await res.json();
      if (data.settings) setSettings(data.settings);
    } catch { /* ignore */ }
  }, []);

  const toggleDisabledTool = useCallback((toolName: string) => {
    setSettings(prev => {
      if (!prev) return prev;
      const list = prev["tools.disabled_tools"] || [];
      const next = list.includes(toolName)
        ? list.filter((t: string) => t !== toolName)
        : [...list, toolName];
      return { ...prev, "tools.disabled_tools": next };
    });
  }, []);

  if (!settings) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center">
        <span className="text-zinc-500 animate-pulse">Chargement...</span>
      </div>
    );
  }

  const isEnterprise = settings.profile === "enterprise";

  const tabs = [
    { id: "general" as const, label: "Général" },
    { id: "security" as const, label: "Sécurité" },
    { id: "tools" as const, label: "Outils" },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center py-8 px-4">
      <div className="max-w-xl w-full">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold">
            {isFirstTime ? "Configuration initiale" : "Réglages"}
          </h1>
          {!isFirstTime && (
            <button
              onClick={onDone}
              className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              Retour
            </button>
          )}
        </div>

        {/* Profile selector */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => applyProfile("personal")}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
              !isEnterprise
                ? "bg-zinc-700 text-zinc-100 ring-1 ring-zinc-500"
                : "bg-zinc-900 text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Personnel
          </button>
          <button
            onClick={() => applyProfile("enterprise")}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
              isEnterprise
                ? "bg-zinc-700 text-zinc-100 ring-1 ring-zinc-500"
                : "bg-zinc-900 text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Entreprise (DSI)
          </button>
        </div>

        {isEnterprise && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
            Mode Entreprise : DeepSeek désactivé, exécution de code bloquée, approbation sur tous les outils.
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-zinc-800 mb-4">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2 text-sm transition-colors border-b-2 -mb-px ${
                activeTab === t.id
                  ? "border-zinc-400 text-zinc-200"
                  : "border-transparent text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-5">

          {/* ── TAB: Général ── */}
          {activeTab === "general" && (
            <>
              <Section title="Modèle IA">
                <label className="block text-xs text-zinc-500 mb-1">Provider</label>
                <div className="space-y-2">
                  {providers.map(p => {
                    const isSelected = settings["llm.provider"] === p.id;
                    return (
                      <button
                        key={p.id}
                        onClick={() => {
                          update("llm.provider", p.id);
                          if (p.models.length > 0) update("llm.model", p.models[0]);
                        }}
                        disabled={!p.configured && !isSelected}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-all text-left ${
                          isSelected
                            ? "bg-zinc-700 ring-1 ring-zinc-500 text-zinc-100"
                            : p.configured
                            ? "bg-zinc-800/50 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
                            : "bg-zinc-900/50 text-zinc-600 cursor-not-allowed"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{p.name}</span>
                          {p.supports_thinking && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Thinking natif
                            </span>
                          )}
                          {!p.supports_thinking && p.configured && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              Thinking simulé
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          {p.configured ? (
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                          ) : (
                            <span className="text-[10px] text-zinc-600">Non configuré</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>

                {(() => {
                  const prov = providers.find(p => p.id === settings["llm.provider"]);
                  if (!prov || prov.models.length === 0) return null;
                  return (
                    <div className="mt-3">
                      <label className="block text-xs text-zinc-500 mb-1">Modèle</label>
                      <select
                        value={settings["llm.model"]}
                        onChange={e => update("llm.model", e.target.value)}
                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                      >
                        {prov.models.map(m => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    </div>
                  );
                })()}
              </Section>

              <Section title="Interface">
                <Toggle
                  label="Afficher les réflexions (thinking)"
                  checked={settings["ui.show_thinking"]}
                  onChange={v => update("ui.show_thinking", v)}
                />
              </Section>

              <Section title="Clés API">
                <p className="text-xs text-zinc-500 mb-2">
                  Ajoute tes clés dans le fichier <code className="bg-zinc-800 px-1 py-0.5 rounded text-zinc-400">backend/.env</code>
                </p>
                <pre className="bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-xs text-zinc-400 font-mono whitespace-pre-wrap">
{`DEEPSEEK_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
OPENAI_API_KEY=sk-...        # optionnel
ANTHROPIC_API_KEY=sk-ant-... # optionnel`}
                </pre>
              </Section>
            </>
          )}

          {/* ── TAB: Sécurité ── */}
          {activeTab === "security" && (
            <>
              <Section title="Exécution de code">
                <Toggle
                  label="Autoriser les calculs Python"
                  description="Si désactivé, l'outil run_local_calculation est bloqué."
                  checked={settings["security.allow_code_execution"]}
                  onChange={v => update("security.allow_code_execution", v)}
                />
                {settings["security.allow_code_execution"] && (
                  <div className="mt-3">
                    <label className="block text-xs text-zinc-500 mb-1">Mode sandbox</label>
                    <select
                      value={settings["security.sandbox_mode"]}
                      onChange={e => update("security.sandbox_mode", e.target.value)}
                      className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                    >
                      <option value="restricted">RestrictedPython (rapide, in-process)</option>
                      <option value="subprocess">Processus isolé (plus sûr)</option>
                    </select>
                  </div>
                )}
              </Section>

              <Section title="Approbation humaine">
                <Toggle
                  label="Demander approbation pour TOUS les outils"
                  description="Par défaut, seuls les outils d'écriture demandent approbation."
                  checked={settings["security.approval_all_tools"]}
                  onChange={v => update("security.approval_all_tools", v)}
                />
              </Section>

              <Section title="Logs centralisés">
                <p className="text-xs text-zinc-500 mb-2">
                  URL d'export SIEM (optionnel, pour la DSI).
                </p>
                <input
                  type="text"
                  placeholder="https://siem.entreprise.com/api/logs"
                  value={settings["security.log_export_url"] || ""}
                  onChange={e => update("security.log_export_url", e.target.value || null)}
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                />
              </Section>
            </>
          )}

          {/* ── TAB: Outils ── */}
          {activeTab === "tools" && (
            <>
              <Section title="Injection dynamique">
                <Toggle
                  label="Activer l'injection dynamique d'outils"
                  description="N'envoie au LLM que les outils pertinents pour chaque message (économise des tokens)."
                  checked={settings["tools.dynamic_injection"]}
                  onChange={v => update("tools.dynamic_injection", v)}
                />
              </Section>

              <Section title="Outils désactivés">
                <p className="text-xs text-zinc-500 mb-3">
                  Désactive des outils spécifiques. L'agent ne pourra plus les utiliser.
                </p>
                {ALL_TOOLS.map(t => (
                  <div key={t.name} className="flex items-center justify-between py-1.5">
                    <div>
                      <span className="text-sm text-zinc-300">{t.label}</span>
                      <span className="ml-2 text-xs text-zinc-600">{t.name}</span>
                    </div>
                    <Toggle
                      label=""
                      checked={!(settings["tools.disabled_tools"] || []).includes(t.name)}
                      onChange={() => toggleDisabledTool(t.name)}
                    />
                  </div>
                ))}
              </Section>
            </>
          )}
        </div>

        {/* Save */}
        <div className="mt-4 flex gap-3">
          <button
            onClick={async () => { await save(); onDone(); }}
            disabled={saving}
            className="flex-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded-xl px-4 py-3 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {saving ? "Enregistrement..." : isFirstTime ? "Commencer" : "Sauvegarder et fermer"}
          </button>
        </div>

        {!isFirstTime && (
          <button
            onClick={onDone}
            className="mt-3 w-full text-zinc-500 hover:text-zinc-300 text-sm transition-colors"
          >
            Annuler
          </button>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <div className="pt-0.5">
        <div
          onClick={e => { e.preventDefault(); onChange(!checked); }}
          className={`w-8 h-[18px] rounded-full transition-colors relative ${
            checked ? "bg-zinc-500" : "bg-zinc-700"
          }`}
        >
          <div
            className={`absolute top-[2px] w-[14px] h-[14px] rounded-full bg-zinc-200 transition-transform ${
              checked ? "translate-x-[16px]" : "translate-x-[2px]"
            }`}
          />
        </div>
      </div>
      <div className="flex-1">
        {label && <span className="text-sm text-zinc-300 group-hover:text-zinc-100 transition-colors">{label}</span>}
        {description && <p className="text-xs text-zinc-600 mt-0.5">{description}</p>}
      </div>
    </label>
  );
}
