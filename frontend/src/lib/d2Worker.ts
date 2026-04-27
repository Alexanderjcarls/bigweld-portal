/** Lazy-loaded D2.js wrapper. Falls back to server-side Kroki on failure. */
import type { } from "@terrastruct/d2";

let d2Module: typeof import("@terrastruct/d2") | null = null;

async function load() {
  if (d2Module) return d2Module;
  d2Module = await import("@terrastruct/d2");
  return d2Module;
}

export async function renderD2(
  source: string,
  onSvg: (svg: string) => void,
  onError: (err: string) => void,
): Promise<void> {
  try {
    const mod = await load();
    const { D2 } = mod;
    const d2 = new D2();
    const result = await d2.compile({ fs: { index: source }, options: { layout: "dagre" } });
    const svg = await d2.render(result.diagram, result.renderOptions);
    onSvg(svg);
  } catch (err) {
    // Fallback to server-side Kroki
    try {
      const r = await fetch("/api/render/kroki", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ diagram_type: "d2", source }),
      });
      if (!r.ok) throw new Error(`kroki: ${r.status}`);
      onSvg(await r.text());
    } catch (fallbackErr) {
      onError(fallbackErr instanceof Error ? fallbackErr.message : String(fallbackErr));
    }
  }
}
