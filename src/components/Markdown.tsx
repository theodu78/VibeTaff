import { useContext, createContext } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Components } from "react-markdown";

const FILE_EXT_RE = /\.(md|txt|json|csv|pdf|doc|docx|xls|xlsx|eml|msg|html|xml|yaml|yml)$/i;
const PATH_LIKE_RE = /^[a-zA-Z0-9_\-\.\/]+$/;
const INLINE_FILE_RE = /(?:^|\s)([\w\-./]+\.(?:md|txt|json|csv|pdf|doc|docx|xls|xlsx|eml|msg))(?=[\s,.:;!?)}\]]|$)/gi;

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
  p({ children, ...props }) {
    return (
      <p {...props}>
        <ClickableFileText>{children}</ClickableFileText>
      </p>
    );
  },
};

function ClickableFileText({ children }: { children?: React.ReactNode }) {
  const onFileOpen = useContext(FileOpenContext);
  if (!onFileOpen) return <>{children}</>;

  const processNode = (node: React.ReactNode): React.ReactNode => {
    if (typeof node !== "string") return node;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    INLINE_FILE_RE.lastIndex = 0;
    let match;
    while ((match = INLINE_FILE_RE.exec(node)) !== null) {
      const fullMatch = match[0];
      const fileName = match[1];
      const matchStart = match.index + (fullMatch.length - fileName.length);
      if (matchStart > lastIndex) {
        parts.push(node.slice(lastIndex, matchStart));
      }
      parts.push(
        <button
          key={`file-${matchStart}`}
          onClick={() => onFileOpen(fileName)}
          className="text-zinc-300 hover:text-white underline underline-offset-2 decoration-zinc-600 hover:decoration-zinc-400 cursor-pointer transition-colors"
          title={`Ouvrir ${fileName}`}
        >
          {fileName}
        </button>
      );
      lastIndex = matchStart + fileName.length;
    }
    if (lastIndex === 0) return node;
    if (lastIndex < node.length) parts.push(node.slice(lastIndex));
    return <>{parts}</>;
  };

  if (!Array.isArray(children)) return <>{processNode(children as React.ReactNode)}</>;
  return <>{(children as React.ReactNode[]).map((c, i) => <span key={i}>{processNode(c)}</span>)}</>;
}

function InlineCode({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) {
  const onFileOpen = useContext(FileOpenContext);
  const text = String(children);

  const hasFileExt = FILE_EXT_RE.test(text);
  const isPath = PATH_LIKE_RE.test(text) && !text.includes(" ");
  const isClickable = (hasFileExt || isPath) && text.length > 1;
  if (isClickable && onFileOpen) {
    return (
      <button
        onClick={() => onFileOpen(text)}
        className="bg-zinc-700/50 px-1.5 py-0.5 rounded text-[0.85em] text-zinc-200 hover:text-white hover:bg-zinc-600/50 cursor-pointer transition-colors underline underline-offset-2 decoration-zinc-600"
        title={`Ouvrir ${text}`}
        {...props}
      >
        {children}
      </button>
    );
  }

  return (
    <code
      className="bg-zinc-700/50 px-1.5 py-0.5 rounded text-[0.85em] text-zinc-200"
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
