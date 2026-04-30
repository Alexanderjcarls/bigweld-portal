import { useChatStore } from "@/v2/stores/chatStore";
import { useContextStats } from "@/v2/hooks/useContextStats";

interface ContextBarProps {
  conversationId?: string;
}

export function ContextBar({ conversationId: conversationIdProp }: ContextBarProps) {
  const storeConversationId = useChatStore((state) => state.conversationId);
  const conversationId = conversationIdProp ?? storeConversationId;
  const { data, isError, isFetching } = useContextStats(conversationId);
  const tokenLimit = data?.tokenLimit ?? 50_000;
  const tokensUsed = data?.tokensUsed ?? 0;
  const percentUsed = clampPercent(data?.percentUsed ?? (tokensUsed / tokenLimit) * 100);

  return (
    <div
      aria-label="Context usage"
      className="hidden min-w-[13rem] items-center gap-2 text-xs text-muted-foreground sm:flex"
      data-testid="context-bar"
      title={`${tokensUsed.toLocaleString()} / ${tokenLimit.toLocaleString()} tokens`}
    >
      <span className="shrink-0 font-medium text-foreground">Context</span>
      <div
        aria-valuemax={tokenLimit}
        aria-valuemin={0}
        aria-valuenow={tokensUsed}
        className="h-2 w-24 overflow-hidden rounded-sm bg-muted"
        role="progressbar"
      >
        <div
          className="h-full rounded-sm transition-[width]"
          style={{
            width: `${percentUsed}%`,
            background:
              "linear-gradient(90deg, var(--hpe-color-foreground-ok) 0%, var(--hpe-color-foreground-warning) 66%, var(--hpe-color-foreground-critical) 100%)",
          }}
        />
      </div>
      <span className="w-24 shrink-0 text-right tabular-nums">
        {tokensUsed.toLocaleString()} / {tokenLimit.toLocaleString()}
      </span>
      {isFetching && <span className="sr-only">Refreshing context usage</span>}
      {isError && <span className="sr-only">Context usage unavailable</span>}
    </div>
  );
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value));
}
