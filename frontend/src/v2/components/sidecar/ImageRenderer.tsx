import { cn } from "@/lib/utils";
import type { ArtifactFile } from "@/v2/stores/artifactsStore";

interface ImageRendererProps {
  body?: string | null;
  files?: ArtifactFile[] | ArtifactFile | null;
  title?: string;
  className?: string;
}

export function ImageRenderer({ body, files, title, className }: ImageRendererProps) {
  const src = imageSource(body, files);

  if (!src) {
    return (
      <div
        className={cn(
          "flex h-full items-center justify-center text-muted-foreground text-sm",
          className,
        )}
        data-testid="image-renderer"
      >
        No image source available.
      </div>
    );
  }

  return (
    <div
      className={cn("flex h-full min-h-0 items-center justify-center overflow-auto p-4", className)}
      data-testid="image-renderer"
    >
      <img
        alt={title ?? "Artifact image"}
        className="max-h-full max-w-full object-contain"
        src={src}
      />
    </div>
  );
}

function imageSource(
  body?: string | null,
  files?: ArtifactFile[] | ArtifactFile | null,
): string | null {
  if (body?.trim()) return body.trim();

  const file = Array.isArray(files) ? files[0] : files;
  if (!file) return null;

  if (typeof file.url === "string") return file.url;
  if (typeof file.data_url === "string") return file.data_url;
  if (typeof file.body_base64 === "string") {
    const mimeType = file.mime_type ?? file.content_type ?? "image/png";
    return `data:${mimeType};base64,${file.body_base64}`;
  }
  if (typeof file.content === "string" && file.content.startsWith("data:")) {
    return file.content;
  }

  return null;
}

