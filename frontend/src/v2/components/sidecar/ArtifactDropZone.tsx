import { UploadIcon } from "lucide-react";
import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ArtifactDropZoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
  compact?: boolean;
}

export function ArtifactDropZone({
  onFiles,
  disabled = false,
  compact = false,
}: ArtifactDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) onFiles(files);
  };

  const handleInput = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length > 0) onFiles(files);
    event.target.value = "";
  };

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 rounded-md border border-dashed bg-muted/30 px-3 py-2 text-sm",
        isDragging && "border-hpe-brand bg-hpe-brand/10",
        disabled && "opacity-60",
        compact ? "min-h-12" : "min-h-20",
      )}
      data-testid="artifact-drop-zone"
      onDragLeave={() => setIsDragging(false)}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div className="flex min-w-0 items-center gap-2">
        <UploadIcon className="size-4 shrink-0 text-muted-foreground" />
        <span className="truncate text-muted-foreground">
          {isDragging ? "Drop to create artifact" : "Drop files into artifacts"}
        </span>
      </div>
      <input
        className="hidden"
        multiple
        onChange={handleInput}
        ref={inputRef}
        type="file"
      />
      <Button
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        size="sm"
        type="button"
        variant="outline"
      >
        Choose
      </Button>
    </div>
  );
}

