import { useState, useEffect, useCallback } from "react";
import type { ContactItem } from "./ContactBlock";

interface ContactViewerProps {
  backendUrl: string;
  projectId: string;
  onClose: () => void;
}

export default function ContactViewer({
  backendUrl,
  projectId,
  onClose,
}: ContactViewerProps) {
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<ContactItem | null>(null);

  const fetchContacts = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/project/${projectId}/contacts`);
      if (res.ok) {
        const data = await res.json();
        setContacts(data.contacts || []);
      }
    } catch { /* */ }
    finally { setLoading(false); }
  }, [backendUrl, projectId]);

  useEffect(() => { fetchContacts(); }, [fetchContacts]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (selected) setSelected(null);
        else onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, selected]);

  const deleteContact = useCallback(async (id: number) => {
    setContacts((prev) => prev.filter((c) => c.id !== id));
    setSelected(null);
    try {
      await fetch(`${backendUrl}/api/project/${projectId}/contacts/${id}`, { method: "DELETE" });
    } catch { fetchContacts(); }
  }, [backendUrl, projectId, fetchContacts]);

  const filtered = search.trim()
    ? contacts.filter((c) => {
        const q = search.toLowerCase();
        return (
          c.nom.toLowerCase().includes(q) ||
          (c.email || "").toLowerCase().includes(q) ||
          (c.entreprise || "").toLowerCase().includes(q) ||
          (c.telephone || "").includes(q)
        );
      })
    : contacts;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg max-h-[80vh] mx-4 bg-zinc-900 border border-zinc-700/50 rounded-xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
            <span className="text-sm font-medium text-zinc-200">Contacts</span>
            <span className="text-xs text-zinc-500">{contacts.length}</span>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-zinc-800" title="Fermer (Esc)">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="shrink-0 px-4 py-2 border-b border-zinc-800/50">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher un contact..."
            className="w-full bg-zinc-800/50 border border-zinc-700/40 rounded-lg px-3 py-1.5 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
          />
        </div>

        {/* List or Detail */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-5 h-5 border-2 border-zinc-700 border-t-zinc-400 rounded-full animate-spin" />
            </div>
          ) : selected ? (
            <div className="p-4 space-y-4">
              <button onClick={() => setSelected(null)} className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Retour
              </button>

              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-zinc-700/50 flex items-center justify-center text-lg text-zinc-300 font-medium">
                  {selected.nom.charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="text-base text-zinc-100 font-medium">{selected.nom}</p>
                  {selected.entreprise && <p className="text-xs text-zinc-500">{selected.entreprise}</p>}
                </div>
              </div>

              <div className="space-y-2.5">
                {selected.telephone && (
                  <div className="flex items-center gap-3 text-sm">
                    <svg className="w-4 h-4 text-zinc-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                    </svg>
                    <span className="text-zinc-300">{selected.telephone}</span>
                  </div>
                )}
                {selected.email && (
                  <div className="flex items-center gap-3 text-sm">
                    <svg className="w-4 h-4 text-zinc-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                    </svg>
                    <span className="text-zinc-300">{selected.email}</span>
                  </div>
                )}
                {selected.adresse && (
                  <div className="flex items-center gap-3 text-sm">
                    <svg className="w-4 h-4 text-zinc-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                    </svg>
                    <span className="text-zinc-300">{selected.adresse}</span>
                  </div>
                )}
                {selected.notes && (
                  <div className="flex items-start gap-3 text-sm">
                    <svg className="w-4 h-4 text-zinc-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    </svg>
                    <span className="text-zinc-400">{selected.notes}</span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-zinc-800/50 flex justify-between items-center">
                <span className="text-xs text-zinc-600">#{selected.id} · ajouté le {selected.cree_le}</span>
                <button
                  onClick={() => deleteContact(selected.id)}
                  className="text-xs text-zinc-600 hover:text-red-400 transition-colors flex items-center gap-1"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Supprimer
                </button>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12 text-sm text-zinc-600">
              {search ? "Aucun contact trouvé." : "Aucun contact. Demandez à l'agent d'en ajouter."}
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/40">
              {filtered.map((contact) => (
                <button
                  key={contact.id}
                  onClick={() => setSelected(contact)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-zinc-800/20 transition-colors text-left"
                >
                  <div className="w-8 h-8 rounded-full bg-zinc-700/50 flex items-center justify-center text-sm text-zinc-400 font-medium shrink-0">
                    {contact.nom.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-zinc-200 truncate">{contact.nom}</p>
                    <p className="text-xs text-zinc-500 truncate">
                      {[contact.entreprise, contact.telephone, contact.email]
                        .filter(Boolean)
                        .join(" · ") || "Aucun détail"}
                    </p>
                  </div>
                  <svg className="w-4 h-4 text-zinc-700 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
