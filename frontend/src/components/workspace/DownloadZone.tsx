import { useChatStore } from "@/stores/chatStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { Button } from "@/components/ui/button";

function svgToPngBlob(svg: string): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth || 1200;
      canvas.height = img.naturalHeight || 800;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0);
      canvas.toBlob(b => {
        URL.revokeObjectURL(url);
        b ? resolve(b) : reject(new Error("toBlob failed"));
      }, "image/png");
    };
    img.onerror = reject;
    img.src = url;
  });
}

export function DownloadZone() {
  const { current, clear } = useWorkspaceStore();
  const conversationId = useChatStore(s => s.conversationId);

  if (!current?.rendered_svg) {
    return (
      <div className="h-full flex items-center justify-center bg-muted/10 border-t font-sans">
        <p className="text-xs text-muted-foreground">Download appears when artifact is ready.</p>
      </div>
    );
  }

  const filenameBase = `bigweld-${current.type}-${Date.now()}`;

  const downloadSvg = async () => {
    const blob = new Blob([current.rendered_svg!], { type: "image/svg+xml" });
    await persistAndDownload(blob, `${filenameBase}.svg`, conversationId);
    clear();
  };
  const downloadPng = async () => {
    const blob = await svgToPngBlob(current.rendered_svg!);
    await persistAndDownload(blob, `${filenameBase}.png`, conversationId);
    clear();
  };
  const downloadSrc = async () => {
    const blob = new Blob([current.source], { type: "text/plain" });
    await persistAndDownload(blob, `${filenameBase}.${current.type}`, conversationId);
    clear();
  };

  return (
    <div className="h-full flex items-center justify-around bg-muted/10 border-t px-6 font-sans">
      <span className="text-sm">Looks good?</span>
      <div className="flex gap-2">
        <Button size="sm" onClick={downloadSvg}>⬇ .svg</Button>
        <Button size="sm" variant="outline" onClick={downloadPng}>.png</Button>
        <Button size="sm" variant="outline" onClick={downloadSrc}>.{current.type}</Button>
      </div>
    </div>
  );
}

async function persistAndDownload(blob: Blob, filename: string, conversationId: string | null) {
  // Server-side persistence (best-effort)
  if (conversationId) {
    try {
      const fd = new FormData();
      fd.append("file", blob, filename);
      await fetch(`/api/output/${conversationId}/${filename}`, { method: "PUT", body: blob });
    } catch { /* swallow — local download still works */ }
  }
  // Local download
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
