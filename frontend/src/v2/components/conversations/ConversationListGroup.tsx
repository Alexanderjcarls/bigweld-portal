import type { ConversationSummary } from "@/v2/lib/api";
import type { ConversationBucket } from "@/v2/hooks/useConversations";
import { ConversationItem } from "@/v2/components/conversations/ConversationItem";

interface ConversationListGroupProps {
  bucket: ConversationBucket;
  conversations: ConversationSummary[];
  activeConversationId?: string;
  onSelect: (conversationId: string) => void;
  onRename: (conversationId: string, title: string) => void;
  onArchive: (conversationId: string) => void;
}

export function ConversationListGroup({
  bucket,
  conversations,
  activeConversationId,
  onSelect,
  onRename,
  onArchive,
}: ConversationListGroupProps) {
  if (conversations.length === 0) return null;
  const bucketId = `conversation-group-${bucket.toLowerCase().replaceAll(" ", "-")}`;

  return (
    <section aria-labelledby={bucketId}>
      <h2
        className="px-2 pb-1 pt-3 text-muted-foreground text-xs font-semibold uppercase"
        id={bucketId}
      >
        {bucket}
      </h2>
      <div className="space-y-1">
        {conversations.map((conversation) => (
          <ConversationItem
            active={conversation.id === activeConversationId}
            conversation={conversation}
            key={conversation.id}
            onArchive={onArchive}
            onRename={onRename}
            onSelect={onSelect}
          />
        ))}
      </div>
    </section>
  );
}
