import { FilePlus2Icon, FolderInputIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ArtifactBody } from "@/v2/components/sidecar/ArtifactBody";
import { ArtifactDropZone } from "@/v2/components/sidecar/ArtifactDropZone";
import { ArtifactHeader } from "@/v2/components/sidecar/ArtifactHeader";
import { ArtifactPicker } from "@/v2/components/sidecar/ArtifactPicker";
import {
  useArtifactVersion,
  useCreateArtifact,
  useCreateDroppedArtifact,
} from "@/v2/hooks/useArtifacts";
import { useArtifactsStore } from "@/v2/stores/artifactsStore";

interface ArtifactSidecarProps {
  conversationId: string;
}

export function ArtifactSidecar({ conversationId }: ArtifactSidecarProps) {
  const isOpen = useArtifactsStore((state) => state.isOpen);
  const activeArtifact = useArtifactsStore((state) => state.activeArtifact);
  const displayVersion = useArtifactsStore((state) => state.displayVersion);
  const receiveMode = useArtifactsStore((state) => state.receiveMode);
  const pickerOpen = useArtifactsStore((state) => state.pickerOpen);
  const setDisplayVersion = useArtifactsStore((state) => state.setDisplayVersion);
  const closeSidecar = useArtifactsStore((state) => state.closeSidecar);
  const closePicker = useArtifactsStore((state) => state.closePicker);
  const openPicker = useArtifactsStore((state) => state.openPicker);
  const createArtifact = useCreateArtifact();
  const droppedArtifact = useCreateDroppedArtifact(conversationId);
  const versionQuery = useArtifactVersion(
    activeArtifact?.id,
    activeArtifact && displayVersion !== activeArtifact.version ? displayVersion : null,
  );
  const displayedArtifact = versionQuery.data ?? activeArtifact;

  if (!isOpen) return null;

  const handleFiles = (files: File[]) => {
    const [file] = files;
    if (!file) return;
    droppedArtifact.mutate(file);
  };

  const handleNewArtifact = () => {
    createArtifact.mutate({
      conv_id: conversationId,
      type: "markdown",
      title: "Untitled artifact",
      source: "user_pasted",
      body: "# Untitled artifact\n",
    });
  };

  return (
    <aside
      aria-label="Artifact sidecar"
      className="z-20 flex h-full w-[min(46vw,720px)] min-w-[380px] flex-col border-border border-l bg-background shadow-xl max-md:absolute max-md:inset-y-0 max-md:right-0 max-md:w-full max-md:min-w-0"
      data-testid="artifact-sidecar"
    >
      <ArtifactHeader
        artifact={displayedArtifact}
        displayVersion={displayVersion}
        onClose={closeSidecar}
        onNextVersion={() => setDisplayVersion(displayVersion + 1)}
        onPreviousVersion={() => setDisplayVersion(displayVersion - 1)}
      />

      <div className="min-h-0 flex-1 overflow-hidden">
        {versionQuery.isLoading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
            Loading version...
          </div>
        ) : versionQuery.error ? (
          <div className="m-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive text-sm">
            Failed to load artifact version.
          </div>
        ) : (
          <ArtifactBody artifact={displayedArtifact} />
        )}
      </div>

      <footer className="shrink-0 space-y-3 border-border border-t bg-background/95 p-3">
        {receiveMode && (
          <ArtifactDropZone
            disabled={droppedArtifact.isPending}
            onFiles={handleFiles}
            compact
          />
        )}
        <div className="flex items-center justify-between gap-2">
          <Button
            disabled={createArtifact.isPending}
            onClick={handleNewArtifact}
            size="sm"
            type="button"
            variant="outline"
          >
            <FilePlus2Icon className="size-4" />
            New artifact
          </Button>
          <Button onClick={openPicker} size="sm" type="button" variant="outline">
            <FolderInputIcon className="size-4" />
            Pull artifact
          </Button>
        </div>
      </footer>

      <ArtifactPicker
        conversationId={conversationId}
        onOpenChange={(open) => {
          if (!open) closePicker();
        }}
        open={pickerOpen}
      />
    </aside>
  );
}

