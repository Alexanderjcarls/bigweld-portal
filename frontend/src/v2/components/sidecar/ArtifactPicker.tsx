import { SearchIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useGlobalArtifacts, usePullArtifact } from "@/v2/hooks/useArtifacts";
import { slugifyArtifactReference } from "@/v2/lib/api";
import type { Artifact } from "@/v2/stores/artifactsStore";

interface ArtifactPickerProps {
  conversationId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ArtifactPicker({ conversationId, open, onOpenChange }: ArtifactPickerProps) {
  const [query, setQuery] = useState("");
  const { data: artifacts = [], isLoading } = useGlobalArtifacts();
  const pullArtifact = usePullArtifact(conversationId);

  const filteredArtifacts = useMemo(
    () => filterArtifacts(artifacts, query),
    [artifacts, query],
  );

  const handleSelect = (artifact: Artifact) => {
    pullArtifact.mutate(artifact, {
      onSuccess: () => onOpenChange(false),
    });
  };

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-h-[80vh] overflow-hidden p-0 sm:max-w-2xl">
        <DialogHeader className="border-border border-b px-5 py-4">
          <DialogTitle>Browse artifacts</DialogTitle>
          <DialogDescription>
            Pull a global artifact into the current conversation.
          </DialogDescription>
        </DialogHeader>
        <div className="flex min-h-0 flex-col">
          <label className="relative m-4 block">
            <SearchIcon className="-translate-y-1/2 pointer-events-none absolute top-1/2 left-3 size-4 text-muted-foreground" />
            <Input
              autoFocus
              className="pl-9"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search title, origin, or type"
              value={query}
            />
          </label>
          <div className="max-h-[48vh] overflow-auto border-border border-t">
            {isLoading ? (
              <div className="px-5 py-8 text-center text-muted-foreground text-sm">
                Loading artifacts...
              </div>
            ) : filteredArtifacts.length === 0 ? (
              <div className="px-5 py-8 text-center text-muted-foreground text-sm">
                No artifacts found.
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {filteredArtifacts.map((artifact) => (
                  <li className="flex items-center justify-between gap-3 px-5 py-3" key={artifact.id}>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{artifact.title}</div>
                      <div className="truncate text-muted-foreground text-xs">
                        {artifact.type} / {artifact.source} / v{artifact.current_version}
                      </div>
                    </div>
                    <Button
                      disabled={pullArtifact.isPending}
                      onClick={() => handleSelect(artifact)}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      Pull
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function filterArtifacts(artifacts: Artifact[], query: string): Artifact[] {
  const needle = slugifyArtifactReference(query);
  if (!needle) return artifacts;

  return artifacts.filter((artifact) => {
    const haystack = slugifyArtifactReference(
      `${artifact.title} ${artifact.type} ${artifact.source} ${artifact.id}`,
    );
    return haystack.includes(needle);
  });
}
