import { useQuery } from "@tanstack/react-query";
import { getBudget } from "@/lib/api";
import { useChatStore } from "@/stores/chatStore";

function Bar({ label, pct, total }: { label: string; pct: number; total?: number }) {
  return (
    <div
      className="flex items-center gap-2 text-xs font-sans"
      title={total ? `${label}: ${total.toLocaleString()} token window` : undefined}
    >
      <span className="text-muted-foreground w-20">{label}</span>
      <div className="w-40 h-2.5 bg-muted rounded overflow-hidden">
        <div
          className="h-full bg-primary transition-all"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-muted-foreground w-16 text-right">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

export function ContextBars() {
  const conversationId = useChatStore(s => s.conversationId);
  const { data } = useQuery({
    queryKey: ["budget", conversationId],
    queryFn: () => getBudget(conversationId),
    refetchInterval: 5000,
    enabled: true,
  });
  return (
    <Bar
      pct={data?.context_window_pct ?? 0}
      label="context"
      total={data?.context_window_total}
    />
  );
}
