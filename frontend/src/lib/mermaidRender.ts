import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
  fontFamily: "HPE Graphik, Inter, system-ui, sans-serif",
});

let _seq = 0;
let _activePromise: Promise<void> | null = null;

export async function renderMermaid(
  source: string,
  onSvg: (svg: string) => void,
  onError: (err: string) => void,
): Promise<void> {
  const id = `mmd-${++_seq}`;
  let promise!: Promise<void>;
  promise = Promise.resolve()
    .then(async () => {
      const { svg } = await mermaid.render(id, source);
      // Single-flight: only deliver if this is still the latest
      if (promise !== _activePromise) return;
      onSvg(svg);
    })
    .catch((err) => {
      if (promise !== _activePromise) return;
      onError(err instanceof Error ? err.message : String(err));
    });
  _activePromise = promise;
  await promise;
}
