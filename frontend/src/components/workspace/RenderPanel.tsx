import { useEffect, useRef, useState } from "react";
import DOMPurify from "dompurify";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { renderMermaid } from "@/lib/mermaidRender";

export function RenderPanel() {
  const { current, setRenderedSvg, setError } = useWorkspaceStore();
  const debounceTimer = useRef<number | undefined>(undefined);
  const [isRendering, setIsRendering] = useState(false);

  useEffect(() => {
    if (!current) return;
    if (debounceTimer.current) window.clearTimeout(debounceTimer.current);
    setIsRendering(true);

    debounceTimer.current = window.setTimeout(async () => {
      try {
        if (current.type === "mermaid") {
          await renderMermaid(current.source, setRenderedSvg, setError);
        } else if (current.type === "d2") {
          // D2 path: lazy-load WASM worker — Phase 10.3
          const { renderD2 } = await import("@/lib/d2Worker");
          await renderD2(current.source, setRenderedSvg, setError);
        } else if (current.type === "kroki") {
          // Server fallback
          const r = await fetch("/api/render/kroki", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              diagram_type: current.diagram_subtype ?? "mermaid",
              source: current.source,
            }),
          });
          if (!r.ok) {
            setError(`kroki: ${r.status}`);
          } else {
            setRenderedSvg(await r.text());
          }
        }
      } finally {
        setIsRendering(false);
      }
    }, 300);

    return () => {
      if (debounceTimer.current) window.clearTimeout(debounceTimer.current);
    };
  }, [current?.source, current?.type, current?.diagram_subtype]);

  if (!current) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground font-sans">
        <p>Working space — Bigweld will render diagrams here.</p>
      </div>
    );
  }

  const sanitizedSvg = current.rendered_svg
    ? DOMPurify.sanitize(current.rendered_svg, {
      USE_PROFILES: { svg: true, svgFilters: true },
    })
    : null;

  return (
    <div className="h-full overflow-auto p-6 relative bg-background">
      {sanitizedSvg ? (
        <div
          className="w-full"
          dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
        />
      ) : current.error ? (
        <div className="text-destructive font-sans">
          <p className="font-semibold">Render error</p>
          <pre className="text-xs mt-2 whitespace-pre-wrap">{current.error}</pre>
        </div>
      ) : (
        <div className="text-muted-foreground font-sans">Rendering…</div>
      )}
      {isRendering && current.rendered_svg && (
        <div className="absolute top-2 right-2 text-xs text-muted-foreground bg-background/80 px-2 py-1 rounded">
          rendering…
        </div>
      )}
    </div>
  );
}
