import { useMemo, useState } from "react";
import { PlusIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConversationListGroup } from "@/v2/components/conversations/ConversationListGroup";
import { ConversationSearch } from "@/v2/components/conversations/ConversationSearch";
import {
  filterConversations,
  groupConversationsByDate,
  useConversations,
} from "@/v2/hooks/useConversations";
import { useChatStore } from "@/v2/stores/chatStore";

export function ConversationSidebar() {
  const [search, setSearch] = useState("");
  const activeConversationId = useChatStore((state) => state.conversationId);
  const resetConversation = useChatStore((state) => state.resetConversation);
  const {
    conversations,
    isLoading,
    isError,
    loadConversation,
    renameConversation,
    archiveConversation,
  } = useConversations();

  const groups = useMemo(
    () => groupConversationsByDate(filterConversations(conversations, search)),
    [conversations, search],
  );

  const handleSelect = (conversationId: string) => {
    loadConversation(conversationId).catch((error: unknown) => {
      console.error("Failed to load v2 conversation:", error);
    });
  };

  return (
    <aside
      aria-label="Conversations"
      className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-muted/20"
    >
      <div className="shrink-0 border-b border-border p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="truncate text-sm font-semibold">Conversations</h2>
          <Button
            aria-label="Start new conversation"
            onClick={resetConversation}
            size="icon-xs"
            type="button"
            variant="ghost"
          >
            <PlusIcon className="size-4" />
          </Button>
        </div>
        <ConversationSearch onChange={setSearch} value={search} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading && (
          <div className="px-2 py-3 text-muted-foreground text-sm">
            Loading conversations...
          </div>
        )}
        {isError && (
          <div className="px-2 py-3 text-destructive text-sm" role="alert">
            Unable to load conversations.
          </div>
        )}
        {!isLoading && !isError && groups.length === 0 && (
          <div className="px-2 py-3 text-muted-foreground text-sm">
            No conversations found.
          </div>
        )}
        {groups.map((group) => (
          <ConversationListGroup
            activeConversationId={activeConversationId}
            bucket={group.bucket}
            conversations={group.conversations}
            key={group.bucket}
            onArchive={(conversationId) => {
              archiveConversation(conversationId).catch((error: unknown) => {
                console.error("Failed to archive v2 conversation:", error);
              });
            }}
            onRename={(conversationId, title) => {
              renameConversation(conversationId, title).catch((error: unknown) => {
                console.error("Failed to rename v2 conversation:", error);
              });
            }}
            onSelect={handleSelect}
          />
        ))}
      </div>
    </aside>
  );
}
