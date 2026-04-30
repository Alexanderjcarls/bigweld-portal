import { useState } from "react";
import { ArchiveIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CompactModal } from "@/v2/components/header/CompactModal";
import { useChatStore } from "@/v2/stores/chatStore";

interface CompactButtonProps {
  conversationId?: string;
  messageCount?: number;
}

export function CompactButton({
  conversationId: conversationIdProp,
  messageCount: messageCountProp,
}: CompactButtonProps) {
  const [open, setOpen] = useState(false);
  const storeConversationId = useChatStore((state) => state.conversationId);
  const storeMessageCount = useChatStore((state) => state.messageCount);
  const conversationId = conversationIdProp ?? storeConversationId;
  const messageCount = messageCountProp ?? storeMessageCount;
  const rangeEndIdx = messageCount - 1;
  const canCompact = messageCount > 0;

  return (
    <>
      <Button
        aria-label="Compact conversation"
        className="text-muted-foreground hover:text-foreground"
        disabled={!canCompact}
        onClick={() => setOpen(true)}
        size="sm"
        type="button"
        variant="ghost"
      >
        <ArchiveIcon className="size-4" />
        <span className="hidden md:inline">Compact</span>
      </Button>
      <CompactModal
        conversationId={conversationId}
        onOpenChange={setOpen}
        open={open}
        rangeEndIdx={rangeEndIdx}
        rangeStartIdx={0}
      />
    </>
  );
}
