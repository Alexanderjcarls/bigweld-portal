import { useQuery } from "@tanstack/react-query";
import { getBudget } from "@/lib/api";

function Bar({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="flex items-center gap-2 font-sans text-sm">
      <span className="text-muted-foreground w-16">{label}</span>
      <div className="h-2.5 w-32 overflow-hidden rounded bg-muted">
        <div className="h-full bg-primary" style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="text-muted-foreground w-10 text-right">{pct.toFixed(0)}%</span>
    </div>
  );
}

export function ContextBars() {
  const { data } = useQuery({
    queryKey: ["budget"],
    queryFn: getBudget,
    refetchInterval: 5000,
  });
  return (
    <div className="flex flex-col gap-1.5">
      <Bar label="conv" pct={data?.conversation_context_pct ?? 0} />
      <Bar label="5h Max" pct={data?.max_5h_pct ?? 0} />
      <Bar label="7d Max" pct={data?.max_7d_pct ?? 0} />
    </div>
  );
}
