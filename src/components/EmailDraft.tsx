import { useState } from "react";

interface EmailDraftProps {
  to: string;
  subject: string;
  body: string;
  mailtoLink: string;
}

export default function EmailDraft({ to, subject, body, mailtoLink }: EmailDraftProps) {
  const [sent, setSent] = useState(false);

  const handleSend = () => {
    window.open(mailtoLink, "_blank");
    setSent(true);
  };

  return (
    <div className="my-2 rounded-lg border border-zinc-700 bg-zinc-900/50 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-zinc-800">
        <span>📧</span>
        <span className="text-xs font-medium text-zinc-400">Brouillon d'email</span>
      </div>

      <div className="px-3 py-2 space-y-2 text-xs">
        <div className="flex gap-2">
          <span className="text-zinc-500 w-10 shrink-0">À :</span>
          <span className="text-zinc-300">{to}</span>
        </div>
        <div className="flex gap-2">
          <span className="text-zinc-500 w-10 shrink-0">Objet :</span>
          <span className="text-zinc-300 font-medium">{subject}</span>
        </div>
        <div className="border-t border-zinc-800 pt-2 mt-2">
          <div className="text-zinc-300 whitespace-pre-wrap leading-relaxed">
            {body}
          </div>
        </div>
      </div>

      <div className="px-3 py-2 border-t border-zinc-800 flex justify-end">
        {sent ? (
          <span className="text-xs text-emerald-400">Client mail ouvert</span>
        ) : (
          <button
            onClick={handleSend}
            className="text-xs bg-blue-600 hover:bg-blue-500 text-white rounded-lg px-3 py-1.5 transition-colors"
          >
            Ouvrir dans le client mail
          </button>
        )}
      </div>
    </div>
  );
}
