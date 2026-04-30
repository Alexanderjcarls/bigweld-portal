import { useState } from "react";
import { ArchiveIcon, FileTextIcon, MoreHorizontalIcon, PencilIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ConversationSummary } from "@/v2/lib/api";
import {
  conversationTitle,
  formatRelativeTime,
} from "@/v2/hooks/useConversations";

interface ConversationItemProps {
  conversation: ConversationSummary;
  active?: boolean;
  onSelect: (conversationId: string) => void;
  onRename: (conversationId: string, title: string) => void;
  onArchive: (conversationId: string) => void;
}

export function ConversationItem({
  conversation,
  active = false,
  onSelect,
  onRename,
  onArchive,
}: ConversationItemProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const title = conversationTitle(conversation);

  const handleRename = () => {
    const nextTitle = window.prompt("Rename conversation", title)?.trim();
    if (nextTitle) onRename(conversation.id, nextTitle);
  };

  return (
    <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
      <div
        className="group relative"
        onContextMenu={(event) => {
          event.preventDefault();
          setMenuOpen(true);
        }}
      >
        <div
          className="flex items-center gap-1 rounded-md pr-1 transition-colors hover:bg-accent focus-within:bg-accent data-[active=true]:bg-accent"
          data-active={active || undefined}
        >
          <button
            aria-current={active ? "page" : undefined}
            className="min-w-0 flex-1 px-2 py-2 text-left outline-none"
            onClick={() => onSelect(conversation.id)}
            type="button"
          >
            <span className="block truncate text-sm font-medium text-foreground">
              {title}
            </span>
            <span className="block text-muted-foreground text-xs">
              {formatRelativeTime(conversation.last_active_at)}
            </span>
          </button>
          {conversation.artifact_count > 0 && (
            <Badge
              aria-label={`${conversation.artifact_count} artifacts`}
              className="gap-1 rounded-sm px-1.5"
              variant="outline"
            >
              <FileTextIcon className="size-3" />
              {conversation.artifact_count}
            </Badge>
          )}
          <DropdownMenuTrigger asChild>
            <Button
              aria-label={`Open actions for ${title}`}
              className="size-7 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100"
              onClick={(event) => event.stopPropagation()}
              size="icon-xs"
              type="button"
              variant="ghost"
            >
              <MoreHorizontalIcon className="size-4" />
            </Button>
          </DropdownMenuTrigger>
        </div>
        <DropdownMenuContent align="end" className="w-36">
          <DropdownMenuItem onClick={handleRename}>
            <PencilIcon className="size-4" />
            Rename
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onArchive(conversation.id)}>
            <ArchiveIcon className="size-4" />
            Archive
          </DropdownMenuItem>
        </DropdownMenuContent>
      </div>
    </DropdownMenu>
  );
}
