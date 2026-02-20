import { useContext, createContext } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Components } from "react-markdown";

const FILE_EXT_RE = /\.(md|txt|json|csv|pdf|doc|docx|xls|xlsx|eml)$/i;
const PATH_LIKE_RE = /^[a-zA-Z0-9_\-\.\/]+$/;

export const FileOpenContext = createContext<
  ((path: string) => void) | null
>(null);

interface MarkdownProps {
  children: string;
  className?: string;
}

const components: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || "");
    const codeString = String(children).replace(/\n$/, "");

    if (match) {
      return (
        <SyntaxHighlighter
          style={oneDark}
          language={match[1]}
          PreTag="div"
          customStyle={{
            margin: "0.5rem 0",
            borderRadius: "0.5rem",
            fontSize: "0.8rem",
          }}
        >
          {codeString}
        </SyntaxHighlighter>
      );
    }

    return <InlineCode {...props}>{children}</InlineCode>;
  },
  a({ href, children, ...props }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-zinc-300 hover:text-zinc-100 underline underline-offset-2 decoration-zinc-600"
        {...props}
      >
        {children}
      </a>
    );
  },
  table({ children, ...props }) {
    return (
      <div className="overflow-x-auto my-2">
        <table
          className="min-w-full text-xs border-collapse border border-zinc-700"
          {...props}
        >
          {children}
        </table>
      </div>
    );
  },
  th({ children, ...props }) {
    return (
      <th
        className="border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-left font-medium text-zinc-300"
        {...props}
      >
        {children}
      </th>
    );
  },
  td({ children, ...props }) {
    return (
      <td
        className="border border-zinc-700 px-3 py-1.5 text-zinc-400"
        {...props}
      >
        {children}
      </td>
    );
  },
};

function InlineCode({ children, ...props }: Record<string, unknown>) {
  const onFileOpen = useContext(FileOpenContext);
  const text = String(children);

  const hasFileExt = FILE_EXT_RE.test(text);
  const isPath = PATH_LIKE_RE.test(text) && !text.includes(" ");
  const isClickable = (hasFileExt || isPath) && text.length > 1;
  if (isClickable && onFileOpen) {
    return (
      <button
        onClick={() => onFileOpen(text)}
        className="bg-zinc-700/50 px-1.5 py-0.5 rounded text-[0.85em] text-emerald-300 hover:text-emerald-200 hover:bg-zinc-600/50 cursor-pointer transition-colors underline underline-offset-2 decoration-zinc-600"
        title={`Ouvrir ${text}`}
        {...props}
      >
        {children}
      </button>
    );
  }

  return (
    <code
      className="bg-zinc-700/50 px-1.5 py-0.5 rounded text-[0.85em] text-emerald-300"
      {...props}
    >
      {children}
    </code>
  );
}

export default function Markdown({ children, className = "" }: MarkdownProps) {
  return (
    <div
      className={`prose prose-sm prose-invert max-w-none
        prose-headings:text-zinc-100 prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1.5
        prose-p:text-zinc-200 prose-p:leading-relaxed prose-p:my-1.5
        prose-strong:text-zinc-100
        prose-ul:my-1.5 prose-ol:my-1.5 prose-li:text-zinc-200 prose-li:my-0.5
        prose-blockquote:border-zinc-600 prose-blockquote:text-zinc-400
        prose-hr:border-zinc-700
        ${className}`}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
