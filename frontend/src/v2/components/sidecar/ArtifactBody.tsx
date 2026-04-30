import { MarkdownRenderer } from "@/v2/components/sidecar/MarkdownRenderer";
import { SpreadsheetRenderer } from "@/v2/components/sidecar/SpreadsheetRenderer";
import { ImageRenderer } from "@/v2/components/sidecar/ImageRenderer";
import { KrokiRenderer } from "@/v2/components/sidecar/KrokiRenderer";
import type { Artifact } from "@/v2/stores/artifactsStore";

interface ArtifactBodyProps {
  artifact: Artifact | null;
}

export function ArtifactBody({ artifact }: ArtifactBodyProps) {
  if (!artifact) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-muted-foreground text-sm">
        Browse, pull, or drop an artifact to open it here.
      </div>
    );
  }

  const body = artifact.body ?? "";

  if (artifact.type === "markdown") {
    return <MarkdownRenderer body={body} className="p-5" />;
  }

  if (artifact.type === "spreadsheet") {
    return <SpreadsheetRenderer body={body} />;
  }

  if (artifact.type === "image") {
    return <ImageRenderer body={artifact.body} files={artifact.files} title={artifact.title} />;
  }

  if (artifact.type === "mermaid" || artifact.type === "d2" || artifact.type === "kroki") {
    return <KrokiRenderer kind={artifact.type} source={body} />;
  }

  return (
    <div className="flex h-full items-center justify-center px-6 text-center text-muted-foreground text-sm">
      Preview unavailable for {artifact.type}.
    </div>
  );
}

