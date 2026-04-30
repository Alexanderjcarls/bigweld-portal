import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { confirmCompact, proposeCompact, type CompactPreview } from "@/v2/lib/api";
import { dispatchContextStatsChatEvent } from "@/v2/hooks/useContextStats";

interface CompactModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conversationId: string;
  rangeStartIdx: number;
  rangeEndIdx: number;
  autoStart?: boolean;
}

type CompactState = "idle" | "previewing" | "ready" | "confirming" | "confirmed" | "error";

export function CompactModal({
  open,
  onOpenChange,
  conversationId,
  rangeStartIdx,
  rangeEndIdx,
  autoStart = true,
}: CompactModalProps) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<CompactState>("idle");
  const [preview, setPreview] = useState<CompactPreview | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const canCompact = rangeEndIdx >= rangeStartIdx;

  useEffect(() => {
    if (!open) {
      setState("idle");
      setPreview(null);
      setErrorMessage(null);
    }
  }, [open]);

  useEffect(() => {
    if (!open || !autoStart || !canCompact || state !== "idle") return;
    void handlePreview();
  });

  const handlePreview = async () => {
    if (!canCompact) return;

    setState("previewing");
    setErrorMessage(null);

    try {
      const nextPreview = await proposeCompact({
        conversationId,
        rangeStartIdx,
        rangeEndIdx,
      });
      setPreview(nextPreview);
      setState("ready");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Compact preview failed");
      setState("error");
    }
  };

  const handleConfirm = async () => {
    if (!preview) return;

    setState("confirming");
    setErrorMessage(null);

    try {
      await confirmCompact({
        conversationId,
        rangeStartIdx,
        rangeEndIdx,
        summary: preview.proposed_summary,
      });
      setState("confirmed");
      dispatchContextStatsChatEvent();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["v2-context-stats", conversationId] }),
        queryClient.invalidateQueries({ queryKey: ["v2-conversations"] }),
      ]);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Compact confirm failed");
      setState("error");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(42rem,calc(100vh-2rem))] overflow-hidden sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Compact conversation</DialogTitle>
          <DialogDescription>
            Review the proposed summary before it is persisted.
          </DialogDescription>
        </DialogHeader>

        {!canCompact && (
          <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
            This conversation does not have messages to compact yet.
          </div>
        )}

        {canCompact && state === "previewing" && (
          <div className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
            Preparing compact preview...
          </div>
        )}

        {preview && (
          <div className="grid min-h-0 gap-3 overflow-hidden">
            <section className="min-h-0">
              <h3 className="mb-2 text-sm font-medium">Summary preview</h3>
              <div className="max-h-40 overflow-auto rounded-md border border-border bg-background px-3 py-2 text-sm">
                {preview.proposed_summary}
              </div>
            </section>
            <section className="min-h-0">
              <h3 className="mb-2 text-sm font-medium">Diff preview</h3>
              <pre className="max-h-64 overflow-auto rounded-md border border-border bg-muted/40 p-3 text-xs leading-relaxed">
                {preview.diff_preview}
              </pre>
            </section>
          </div>
        )}

        {state === "confirmed" && (
          <div className="rounded-md border border-hpe-status-ok/40 bg-hpe-status-ok/10 px-3 py-2 text-hpe-status-ok text-sm">
            Compact summary persisted.
          </div>
        )}

        {errorMessage && (
          <div
            className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-destructive text-sm"
            role="alert"
          >
            {errorMessage}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Close
          </Button>
          <Button
            disabled={!canCompact || state === "previewing" || state === "confirming"}
            onClick={preview ? handleConfirm : handlePreview}
            type="button"
          >
            {preview ? compactConfirmLabel(state) : compactPreviewLabel(state)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function compactPreviewLabel(state: CompactState): string {
  return state === "previewing" ? "Preparing" : "Generate preview";
}

function compactConfirmLabel(state: CompactState): string {
  if (state === "confirming") return "Persisting";
  if (state === "confirmed") return "Confirmed";
  return "Confirm compact";
}
