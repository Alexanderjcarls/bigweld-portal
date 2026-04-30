import DOMPurify from "dompurify";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const KROKI_BASE_URL = "http://192.168.0.30:8889";

interface KrokiRendererProps {
  source: string;
  kind: "mermaid" | "d2" | "kroki";
  className?: string;
}

interface KrokiState {
  key: string;
  svg: string | null;
  error: string | null;
}

export function KrokiRenderer({ source, kind, className }: KrokiRendererProps) {
  const diagramKind = kind === "kroki" ? "mermaid" : kind;
  const renderKey = `${diagramKind}:${source}`;
  const [result, setResult] = useState<KrokiState>({
    key: "",
    svg: null,
    error: null,
  });
  const current =
    result.key === renderKey
      ? result
      : {
          key: renderKey,
          svg: null,
          error: source.trim() ? null : "No diagram source available.",
        };

  useEffect(() => {
    if (!source.trim()) return;

    const controller = new AbortController();

    fetch(`${KROKI_BASE_URL}/${diagramKind}/svg`, {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: source,
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`kroki: ${response.status}`);
        return response.text();
      })
      .then((rawSvg) => {
        setResult({
          key: renderKey,
          svg: DOMPurify.sanitize(rawSvg, { USE_PROFILES: { svg: true, svgFilters: true } }),
          error: null,
        });
      })
      .catch((renderError: unknown) => {
        if (controller.signal.aborted) return;
        setResult({
          key: renderKey,
          svg: null,
          error: renderError instanceof Error ? renderError.message : String(renderError),
        });
      });

    return () => controller.abort();
  }, [diagramKind, renderKey, source]);

  return (
    <div
      className={cn("flex h-full min-h-0 items-center justify-center overflow-auto p-4", className)}
      data-testid="kroki-renderer"
    >
      {current.svg ? (
        <div className="max-h-full max-w-full" dangerouslySetInnerHTML={{ __html: current.svg }} />
      ) : current.error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive text-sm">
          {current.error}
        </div>
      ) : (
        <div className="text-muted-foreground text-sm">Rendering diagram...</div>
      )}
    </div>
  );
}
