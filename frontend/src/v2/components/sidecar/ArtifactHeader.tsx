import {
  ArrowLeftIcon,
  ArrowRightIcon,
  DownloadIcon,
  MoreHorizontalIcon,
  NetworkIcon,
  PencilIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDeleteArtifact } from "@/v2/hooks/useArtifacts";
import type { Artifact } from "@/v2/stores/artifactsStore";
import { useArtifactsStore } from "@/v2/stores/artifactsStore";

interface ArtifactHeaderProps {
  artifact: Artifact | null;
  displayVersion: number;
  onPreviousVersion: () => void;
  onNextVersion: () => void;
  onClose: () => void;
}

export function ArtifactHeader({
  artifact,
  displayVersion,
  onPreviousVersion,
  onNextVersion,
  onClose,
}: ArtifactHeaderProps) {
  const updateActiveArtifact = useArtifactsStore((state) => state.updateActiveArtifact);
  const deleteArtifact = useDeleteArtifact();
  const currentVersion = artifact?.current_version ?? 1;

  const handleRename = () => {
    if (!artifact) return;
    const nextTitle = window.prompt("Rename artifact", artifact.title)?.trim();
    if (!nextTitle) return;
    updateActiveArtifact({ ...artifact, title: nextTitle });
  };

  const handleDelete = () => {
    if (!artifact) return;
    deleteArtifact.mutate(artifact.id);
  };

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-border border-b px-3">
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <div className="truncate text-sm font-semibold">
            {artifact?.title ?? "Artifacts"}
          </div>
          {artifact && (
            <span className="shrink-0 rounded-sm border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground uppercase">
              {originTag(artifact.source)}
            </span>
          )}
        </div>
        <div className="truncate text-muted-foreground text-xs">
          {artifact ? originLabel(artifact.source) : "Global library"}
        </div>
      </div>

      {artifact && (
        <div className="flex shrink-0 items-center gap-1" aria-label="Artifact versions">
          <Button
            aria-label="Previous artifact version"
            disabled={displayVersion <= 1}
            onClick={onPreviousVersion}
            size="icon-xs"
            type="button"
            variant="ghost"
          >
            <ArrowLeftIcon className="size-3.5" />
          </Button>
          <span className="min-w-12 text-center text-muted-foreground text-xs">
            v{displayVersion}/{currentVersion}
          </span>
          <Button
            aria-label="Next artifact version"
            disabled={displayVersion >= currentVersion}
            onClick={onNextVersion}
            size="icon-xs"
            type="button"
            variant="ghost"
          >
            <ArrowRightIcon className="size-3.5" />
          </Button>
        </div>
      )}

      {artifact && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button aria-label="Artifact actions" size="icon-sm" type="button" variant="ghost">
              <MoreHorizontalIcon className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={handleRename}>
              <PencilIcon className="size-4" />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => exportArtifact(artifact)}>
              <DownloadIcon className="size-4" />
              Export
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => window.alert("Use write_node to promote this artifact to the graph.")}>
              <NetworkIcon className="size-4" />
              Commit to graph
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleDelete} variant="destructive">
              <Trash2Icon className="size-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      <Button aria-label="Close artifact sidecar" onClick={onClose} size="icon-sm" type="button" variant="ghost">
        <XIcon className="size-4" />
      </Button>
    </header>
  );
}

function originLabel(source: Artifact["source"]): string {
  switch (source) {
    case "bigweld":
      return "Created by Bigweld";
    case "user_dropped":
      return "User dropped";
    case "user_pasted":
      return "User pasted";
    case "cross_conv_pulled":
      return "Pulled from another conversation";
  }
}

function originTag(source: Artifact["source"]): string {
  switch (source) {
    case "bigweld":
      return "bigweld";
    case "user_dropped":
      return "dropped";
    case "user_pasted":
      return "pasted";
    case "cross_conv_pulled":
      return "pulled";
  }
}

function exportArtifact(artifact: Artifact): void {
  const body = artifact.body ?? JSON.stringify(artifact.files ?? {}, null, 2);
  const extension = extensionForType(artifact.type);
  const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${safeFilename(artifact.title)}.${extension}`;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function extensionForType(type: Artifact["type"]): string {
  if (type === "spreadsheet") return "csv";
  if (type === "mermaid") return "mmd";
  return type;
}

function safeFilename(value: string): string {
  return value.trim().replace(/[^a-z0-9._-]+/gi, "-").replace(/^-+|-+$/g, "") || "artifact";
}
