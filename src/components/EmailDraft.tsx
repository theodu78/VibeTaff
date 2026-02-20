import { useState, useCallback } from "react";

interface EmailDraftProps {
  to: string;
  subject: string;
  body: string;
  mailtoLink: string;
}

export default function EmailDraft({ to, subject, body, mailtoLink }: EmailDraftProps) {
  const [copied, setCopied] = useState(false);

  const handleOpen = () => {
    window.open(mailtoLink, "_blank");
  };

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(body);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* */ }
  }, [body]);

  return (
    <div className="my-3 rounded-xl border border-zinc-700/50 bg-zinc-800/40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-zinc-700/30 bg-zinc-800/30">
        <svg className="w-4 h-4 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
        </svg>
        <span className="text-xs font-medium text-zinc-400">Brouillon d'email</span>
      </div>

      {/* Meta */}
      <div className="px-4 py-2.5 space-y-1.5 border-b border-zinc-700/30">
        <div className="flex gap-2 text-sm">
          <span className="text-zinc-500 w-12 shrink-0">À</span>
          <span className="text-zinc-200">{to}</span>
        </div>
        <div className="flex gap-2 text-sm">
          <span className="text-zinc-500 w-12 shrink-0">Objet</span>
          <span className="text-zinc-200 font-medium">{subject}</span>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 max-h-64 overflow-y-auto">
        <div className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
          {body}
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 py-2.5 border-t border-zinc-700/30 bg-zinc-800/20 flex items-center justify-between gap-2">
        <button
          onClick={handleCopy}
          className="text-xs text-zinc-500 hover:text-zinc-300 flex items-center gap-1.5 transition-colors"
        >
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copié
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copier le corps
            </>
          )}
        </button>

        <button
          onClick={handleOpen}
          className="text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-lg px-3.5 py-1.5 font-medium transition-colors flex items-center gap-1.5"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          Ouvrir dans le client mail
        </button>
      </div>
    </div>
  );
}
