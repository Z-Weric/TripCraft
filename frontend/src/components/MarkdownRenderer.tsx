import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={`markdown-body ${className || ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-black font-display text-foreground mb-3 mt-4">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-bold font-display text-foreground mb-2 mt-4 border-l-4 border-primary pl-3">{children}</h2>,
          h3: ({ children }) => <h3 className="text-lg font-bold font-display text-foreground mb-1 mt-3">{children}</h3>,
          p: ({ children }) => <p className="text-sm text-foreground-secondary leading-relaxed mb-3">{children}</p>,
          ul: ({ children }) => <ul className="list-none mb-3 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal ml-4 mb-3 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="text-sm text-foreground-secondary leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-bold text-foreground">{children}</strong>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary-light pl-3 py-1 my-2 text-sm text-foreground-secondary italic bg-background-tertiary rounded-r-sm">
              {children}
            </blockquote>
          ),
          code: ({ children }) => <code className="bg-background-tertiary px-1.5 py-0.5 rounded text-xs font-mono text-primary">{children}</code>,
          hr: () => <hr className="border-border-light my-4" />,
          a: ({ children, href }) => <a href={href} className="text-primary hover:underline" target="_blank" rel="noreferrer">{children}</a>,
          table: ({ children }) => <table className="w-full text-xs border border-border mb-3">{children}</table>,
          th: ({ children }) => <th className="border border-border p-2 bg-background-tertiary font-bold">{children}</th>,
          td: ({ children }) => <td className="border border-border p-2">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}