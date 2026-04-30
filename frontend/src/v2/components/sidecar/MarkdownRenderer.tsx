import DOMPurify from "dompurify";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { codeToHtml } from "shiki";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  body: string;
  className?: string;
}

export function MarkdownRenderer({ body, className }: MarkdownRendererProps) {
  const components = useMemo<Components>(
    () => ({
      code({ children, className: codeClassName, node: _node, ...props }) {
        const code = textFromChildren(children).replace(/\n$/, "");
        const language = languageFromClassName(codeClassName);

        if (!language) {
          return (
            <code
              className={cn(
                "rounded-sm bg-muted px-1 py-0.5 font-mono text-[0.85em]",
                codeClassName,
              )}
              {...props}
            >
              {children}
            </code>
          );
        }

        return <ShikiCodeBlock code={code} language={language} />;
      },
      table({ children }) {
        return (
          <div className="my-4 overflow-x-auto rounded-md border border-border">
            <table className="min-w-full border-collapse text-sm">{children}</table>
          </div>
        );
      },
      th({ children }) {
        return (
          <th className="border-border border-b bg-muted px-3 py-2 text-left font-semibold">
            {children}
          </th>
        );
      },
      td({ children }) {
        return <td className="border-border border-t px-3 py-2 align-top">{children}</td>;
      },
    }),
    [],
  );

  return (
    <div
      className={cn(
        "artifact-markdown max-w-none text-sm leading-6",
        "[&_a]:text-primary [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground",
        "[&_h1]:mt-0 [&_h1]:mb-4 [&_h1]:text-2xl [&_h1]:font-semibold",
        "[&_h2]:mt-6 [&_h2]:mb-3 [&_h2]:text-lg [&_h2]:font-semibold",
        "[&_h3]:mt-5 [&_h3]:mb-2 [&_h3]:text-base [&_h3]:font-semibold",
        "[&_li]:my-1 [&_ol]:my-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-3 [&_ul]:my-3 [&_ul]:list-disc [&_ul]:pl-5",
        className,
      )}
      data-testid="markdown-renderer"
    >
      <ReactMarkdown components={components} remarkPlugins={[remarkGfm]}>
        {body}
      </ReactMarkdown>
    </div>
  );
}

interface ShikiCodeBlockProps {
  code: string;
  language: string;
}

function ShikiCodeBlock({ code, language }: ShikiCodeBlockProps) {
  const [html, setHtml] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    codeToHtml(code, {
      lang: language,
      theme: "github-dark",
    })
      .then((highlighted) => {
        if (!cancelled) {
          setHtml(DOMPurify.sanitize(highlighted));
        }
      })
      .catch(() => {
        if (!cancelled) setHtml(null);
      });

    return () => {
      cancelled = true;
    };
  }, [code, language]);

  if (!html) {
    return (
      <pre className="my-4 overflow-x-auto rounded-md border border-border bg-muted p-3">
        <code className="font-mono text-xs">{code}</code>
      </pre>
    );
  }

  return (
    <div
      className="my-4 overflow-x-auto rounded-md border border-border [&_pre]:m-0 [&_pre]:p-3 [&_pre]:text-xs"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function languageFromClassName(className?: string): string | null {
  const match = /language-(\S+)/.exec(className ?? "");
  return match?.[1] ?? null;
}

function textFromChildren(children: ReactNode): string {
  if (children === null || children === undefined) return "";
  if (Array.isArray(children)) return children.map(textFromChildren).join("");
  return String(children);
}
