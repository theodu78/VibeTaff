import { useState, useCallback } from "react";

export interface ContactItem {
  id: number;
  nom: string;
  telephone?: string;
  email?: string;
  adresse?: string;
  entreprise?: string;
  notes?: string;
  cree_le?: string;
}

interface ContactBlockProps {
  contacts: ContactItem[];
  onOpenViewer?: () => void;
}

export default function ContactBlock({
  contacts: initialContacts,
  onOpenViewer,
}: ContactBlockProps) {
  const [contacts] = useState<ContactItem[]>(initialContacts);

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
            d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
          />
        </svg>
        <span className="text-sm text-zinc-300 font-medium">Contacts</span>
        <span className="text-sm text-zinc-500">{contacts.length}</span>
      </button>

      <div className="border-t border-zinc-800/50">
        {contacts.slice(0, 5).map((contact) => (
          <div
            key={contact.id}
            className="flex items-center gap-2.5 px-4 py-2 hover:bg-zinc-700/15 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-zinc-700/50 flex items-center justify-center text-xs text-zinc-400 font-medium shrink-0">
              {contact.nom.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-zinc-300 truncate">{contact.nom}</p>
              <p className="text-xs text-zinc-500 truncate">
                {[contact.entreprise, contact.telephone, contact.email]
                  .filter(Boolean)
                  .join(" · ") || "Aucun détail"}
              </p>
            </div>
          </div>
        ))}
        {contacts.length > 5 && (
          <button
            onClick={onOpenViewer}
            className="w-full text-xs text-zinc-500 hover:text-zinc-300 py-2 transition-colors"
          >
            + {contacts.length - 5} autre{contacts.length - 5 > 1 ? "s" : ""}
          </button>
        )}
      </div>
    </div>
  );
}
