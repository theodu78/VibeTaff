import { useEditor, EditorContent } from "@tiptap/react";
import { StarterKit } from "@tiptap/starter-kit";
import { Table, TableRow, TableCell, TableHeader } from "@tiptap/extension-table";
import { useCallback, useState } from "react";

interface DocumentEditorProps {
  content: string;
  onSave: (markdown: string) => Promise<void>;
  fileName: string;
}

function markdownToHtml(md: string): string {
  let html = md;

  html = html.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/`(.+?)`/g, "<code>$1</code>");
  html = html.replace(/~~(.+?)~~/g, "<s>$1</s>");

  html = html.replace(/^---$/gm, "<hr>");

  const lines = html.split("\n");
  const result: string[] = [];
  let inList = false;

  for (const line of lines) {
    if (/^[-*] /.test(line.trim())) {
      if (!inList) {
        result.push("<ul>");
        inList = true;
      }
      result.push(`<li>${line.trim().slice(2)}</li>`);
    } else {
      if (inList) {
        result.push("</ul>");
        inList = false;
      }
      if (line.trim() === "") {
        result.push("<p></p>");
      } else if (!line.startsWith("<h") && !line.startsWith("<hr")) {
        result.push(`<p>${line}</p>`);
      } else {
        result.push(line);
      }
    }
  }
  if (inList) result.push("</ul>");

  const tableRegex =
    /(<p>\|.+\|<\/p>\n?(<p>\|[-|: ]+\|<\/p>\n?)?(<p>\|.+\|<\/p>\n?)*)/g;
  html = result.join("\n");
  html = html.replace(tableRegex, (block) => {
    const rows = block
      .split("\n")
      .filter((l) => l.includes("|"))
      .map((l) =>
        l
          .replace(/<\/?p>/g, "")
          .trim()
          .replace(/^\||\|$/g, "")
          .split("|")
          .map((c) => c.trim())
      );

    if (rows.length < 2) return block;
    const isSep = (r: string[]) => r.every((c) => /^[-: ]+$/.test(c));
    const filtered = rows.filter((r) => !isSep(r));
    if (filtered.length === 0) return block;

    let table = "<table><thead><tr>";
    filtered[0].forEach((c) => (table += `<th>${c}</th>`));
    table += "</tr></thead><tbody>";
    for (let i = 1; i < filtered.length; i++) {
      table += "<tr>";
      filtered[i].forEach((c) => (table += `<td>${c}</td>`));
      table += "</tr>";
    }
    table += "</tbody></table>";
    return table;
  });

  return html;
}

function htmlToMarkdown(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;

  function walk(node: Node): string {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent || "";
    if (node.nodeType !== Node.ELEMENT_NODE) return "";

    const el = node as HTMLElement;
    const tag = el.tagName.toLowerCase();
    const children = Array.from(el.childNodes).map(walk).join("");

    switch (tag) {
      case "h1": return `# ${children}\n\n`;
      case "h2": return `## ${children}\n\n`;
      case "h3": return `### ${children}\n\n`;
      case "h4": return `#### ${children}\n\n`;
      case "strong": case "b": return `**${children}**`;
      case "em": case "i": return `*${children}*`;
      case "s": case "del": return `~~${children}~~`;
      case "code": return `\`${children}\``;
      case "hr": return "---\n\n";
      case "br": return "\n";
      case "p": return children.trim() ? `${children}\n\n` : "\n";
      case "ul": return children;
      case "ol": return children;
      case "li": return `- ${children}\n`;
      case "table": return convertTable(el) + "\n\n";
      default: return children;
    }
  }

  function convertTable(table: HTMLElement): string {
    const rows = table.querySelectorAll("tr");
    if (rows.length === 0) return "";

    const lines: string[] = [];
    rows.forEach((row, ri) => {
      const cells = Array.from(row.querySelectorAll("th, td"));
      const line = "| " + cells.map((c) => c.textContent?.trim() || "").join(" | ") + " |";
      lines.push(line);
      if (ri === 0) {
        lines.push("| " + cells.map(() => "---").join(" | ") + " |");
      }
    });
    return lines.join("\n");
  }

  return walk(div).replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

const ToolbarButton = ({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void;
  active?: boolean;
  title: string;
  children: React.ReactNode;
}) => (
  <button
    onClick={onClick}
    title={title}
    className={`p-1.5 rounded transition-colors ${
      active
        ? "bg-zinc-600 text-zinc-100"
        : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/50"
    }`}
  >
    {children}
  </button>
);

export default function DocumentEditor({ content, onSave, fileName }: DocumentEditorProps) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: markdownToHtml(content),
    editorProps: {
      attributes: {
        class:
          "prose prose-sm prose-invert max-w-none focus:outline-none min-h-[200px] px-1",
      },
    },
  });

  const handleSave = useCallback(async () => {
    if (!editor) return;
    setSaving(true);
    const html = editor.getHTML();
    const md = htmlToMarkdown(html);
    await onSave(md);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, [editor, onSave]);

  if (!editor) return null;

  return (
    <div>
      {/* Toolbar */}
      <div className="sticky top-0 z-20 flex items-center gap-0.5 px-2 py-1.5 border-b border-zinc-800 bg-zinc-900 flex-wrap">
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive("bold")}
          title="Gras (Ctrl+B)"
        >
          <span className="text-xs font-bold w-5 h-5 flex items-center justify-center">B</span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive("italic")}
          title="Italique (Ctrl+I)"
        >
          <span className="text-xs italic w-5 h-5 flex items-center justify-center">I</span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleStrike().run()}
          active={editor.isActive("strike")}
          title="Barré"
        >
          <span className="text-xs line-through w-5 h-5 flex items-center justify-center">S</span>
        </ToolbarButton>

        <div className="w-px h-5 bg-zinc-700 mx-1" />

        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          active={editor.isActive("heading", { level: 1 })}
          title="Titre 1"
        >
          <span className="text-xs font-bold w-5 h-5 flex items-center justify-center">H1</span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          active={editor.isActive("heading", { level: 2 })}
          title="Titre 2"
        >
          <span className="text-xs font-bold w-5 h-5 flex items-center justify-center">H2</span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          active={editor.isActive("heading", { level: 3 })}
          title="Titre 3"
        >
          <span className="text-xs font-bold w-5 h-5 flex items-center justify-center">H3</span>
        </ToolbarButton>

        <div className="w-px h-5 bg-zinc-700 mx-1" />

        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive("bulletList")}
          title="Liste à puces"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive("orderedList")}
          title="Liste numérotée"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h10M7 16h10M3 8h.01M3 12h.01M3 16h.01" />
          </svg>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          active={editor.isActive("blockquote")}
          title="Citation"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </ToolbarButton>

        <div className="w-px h-5 bg-zinc-700 mx-1" />

        <ToolbarButton
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
          title="Séparateur"
        >
          <span className="text-xs w-5 h-5 flex items-center justify-center">—</span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() =>
            editor
              .chain()
              .focus()
              .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
              .run()
          }
          title="Insérer tableau"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18M10 3v18M14 3v18M3 6a3 3 0 013-3h12a3 3 0 013 3v12a3 3 0 01-3 3H6a3 3 0 01-3-3V6z" />
          </svg>
        </ToolbarButton>

        <div className="w-px h-5 bg-zinc-700 mx-1" />

        <ToolbarButton
          onClick={() => editor.chain().focus().undo().run()}
          title="Annuler (Ctrl+Z)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a5 5 0 015 5v2M3 10l4-4M3 10l4 4" />
          </svg>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().redo().run()}
          title="Refaire (Ctrl+Shift+Z)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10H11a5 5 0 00-5 5v2M21 10l-4-4M21 10l-4 4" />
          </svg>
        </ToolbarButton>

        <div className="ml-auto flex items-center gap-2">
          {saved && (
            <span className="text-xs text-emerald-500 animate-pulse">Sauvegardé</span>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1 rounded-md text-xs font-medium bg-zinc-700 hover:bg-zinc-600 text-zinc-200 transition-colors disabled:opacity-50"
          >
            {saving ? "..." : "Sauvegarder"}
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="p-4">
        <EditorContent editor={editor} />
      </div>

      {/* Footer */}
      <div className="sticky bottom-0 flex items-center justify-between px-4 py-2 border-t border-zinc-800 bg-zinc-900 text-xs text-zinc-600">
        <span>{fileName}</span>
        <span>
          {editor.storage.characterCount?.characters?.() ??
            editor.getText().length}{" "}
          caractères
        </span>
      </div>
    </div>
  );
}
