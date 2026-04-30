import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { UIMessage } from "ai";
import {
  getV2Conversation,
  listV2Conversations,
  patchV2Conversation,
  type ConversationMessageRecord,
  type ConversationSummary,
} from "@/v2/lib/api";
import { useChatStore } from "@/v2/stores/chatStore";

export type ConversationBucket =
  | "Today"
  | "Yesterday"
  | "This Week"
  | "This Month"
  | "Older";

export const CONVERSATION_BUCKETS: ConversationBucket[] = [
  "Today",
  "Yesterday",
  "This Week",
  "This Month",
  "Older",
];

export interface ConversationGroup {
  bucket: ConversationBucket;
  conversations: ConversationSummary[];
}

export function useConversations(options: { archived?: boolean } = {}) {
  const queryClient = useQueryClient();
  const setConversationId = useChatStore((state) => state.setConversationId);
  const hydrateConversation = useChatStore((state) => state.hydrateConversation);

  const query = useQuery({
    queryKey: ["v2-conversations", options.archived ?? false],
    queryFn: () => listV2Conversations(options),
    retry: false,
  });

  const patchMutation = useMutation({
    mutationFn: (variables: {
      conversationId: string;
      title?: string;
      archived?: boolean;
    }) =>
      patchV2Conversation(variables.conversationId, {
        title: variables.title,
        archived: variables.archived,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["v2-conversations"] });
    },
  });

  const loadConversation = async (conversationId: string) => {
    setConversationId(conversationId);
    const detail = await getV2Conversation(conversationId);
    hydrateConversation(conversationId, conversationRecordsToUIMessages(detail.messages));
    return detail;
  };

  return {
    ...query,
    conversations: query.data ?? [],
    loadConversation,
    renameConversation: (conversationId: string, title: string) =>
      patchMutation.mutateAsync({ conversationId, title }),
    archiveConversation: (conversationId: string) =>
      patchMutation.mutateAsync({ conversationId, archived: true }),
    isPatching: patchMutation.isPending,
  };
}

export function filterConversations(
  conversations: ConversationSummary[],
  search: string,
): ConversationSummary[] {
  const normalizedSearch = search.trim().toLowerCase();
  if (!normalizedSearch) return conversations;

  return conversations.filter((conversation) =>
    conversationTitle(conversation).toLowerCase().includes(normalizedSearch),
  );
}

export function groupConversationsByDate(
  conversations: ConversationSummary[],
  now = new Date(),
): ConversationGroup[] {
  const groups = new Map<ConversationBucket, ConversationSummary[]>(
    CONVERSATION_BUCKETS.map((bucket) => [bucket, []]),
  );

  for (const conversation of conversations) {
    groups.get(bucketConversation(conversation, now))?.push(conversation);
  }

  return CONVERSATION_BUCKETS.map((bucket) => ({
    bucket,
    conversations: groups.get(bucket) ?? [],
  })).filter((group) => group.conversations.length > 0);
}

export function bucketConversation(
  conversation: ConversationSummary,
  now = new Date(),
): ConversationBucket {
  const lastActive = new Date(conversation.last_active_at);
  if (!Number.isFinite(lastActive.getTime())) return "Older";

  const todayStart = startOfDay(now);
  const yesterdayStart = new Date(todayStart);
  yesterdayStart.setDate(todayStart.getDate() - 1);
  const weekStart = startOfWeek(todayStart);
  const monthStart = new Date(todayStart.getFullYear(), todayStart.getMonth(), 1);

  if (lastActive >= todayStart) return "Today";
  if (lastActive >= yesterdayStart) return "Yesterday";
  if (lastActive >= weekStart) return "This Week";
  if (lastActive >= monthStart) return "This Month";
  return "Older";
}

export function conversationTitle(conversation: Pick<ConversationSummary, "id" | "title">): string {
  return conversation.title?.trim() || `Conversation ${conversation.id.slice(0, 8)}`;
}

export function formatRelativeTime(value: string, now = new Date()): string {
  const date = new Date(value);
  const diffMs = now.getTime() - date.getTime();
  if (!Number.isFinite(diffMs)) return "unknown";
  if (diffMs < 60_000) return "just now";

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() === now.getFullYear() ? undefined : "numeric",
  });
}

export function conversationRecordsToUIMessages(
  records: ConversationMessageRecord[],
): UIMessage[] {
  return records
    .map((record, index) => conversationRecordToUIMessage(record, index))
    .filter((message) => message !== null);
}

function conversationRecordToUIMessage(
  record: ConversationMessageRecord,
  index: number,
): UIMessage | null {
  const rawMessage = uiMessageFromRaw(record.raw_message);
  if (rawMessage) return rawMessage;

  const role = normalizeRole(record.role);
  if (!role) return null;

  return {
    id: String(record.id ?? record.turn_idx ?? `message-${index}`),
    role,
    parts: [{ type: "text", text: record.content ?? "" }],
  };
}

function uiMessageFromRaw(raw: unknown): UIMessage | null {
  if (!raw || typeof raw !== "object") return null;
  const candidate = raw as Partial<UIMessage>;

  if (
    typeof candidate.id === "string" &&
    normalizeRole(candidate.role) &&
    Array.isArray(candidate.parts)
  ) {
    return {
      id: candidate.id,
      role: normalizeRole(candidate.role) ?? "assistant",
      parts: candidate.parts,
    } as UIMessage;
  }

  return null;
}

function normalizeRole(role: unknown): UIMessage["role"] | null {
  if (role === "system" || role === "user" || role === "assistant") return role;
  return null;
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function startOfWeek(date: Date): Date {
  const start = startOfDay(date);
  const day = start.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  start.setDate(start.getDate() + mondayOffset);
  return start;
}
