import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getContextStats, type ContextStats } from "@/v2/lib/api";

export const CONTEXT_STATS_CHAT_EVENT = "bigweld:v2:chat-event";

export function useContextStats(conversationId: string | null | undefined) {
  const query = useQuery<ContextStats>({
    queryKey: ["v2-context-stats", conversationId],
    queryFn: () => getContextStats(conversationId ?? ""),
    enabled: Boolean(conversationId),
    refetchInterval: 10_000,
    retry: false,
  });

  useEffect(() => {
    const handleChatEvent = () => {
      void query.refetch();
    };

    window.addEventListener(CONTEXT_STATS_CHAT_EVENT, handleChatEvent);
    return () => window.removeEventListener(CONTEXT_STATS_CHAT_EVENT, handleChatEvent);
  }, [query]);

  return query;
}

export function dispatchContextStatsChatEvent(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(CONTEXT_STATS_CHAT_EVENT));
}
