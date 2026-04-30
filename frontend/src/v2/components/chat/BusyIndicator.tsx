import { CogIcon } from "lucide-react";

export interface ActivityEvent {
  type?: "reasoning" | "tool" | "default";
  toolName?: string | null;
  input?: unknown;
  label?: string | null;
}

interface BusyIndicatorProps {
  activity?: ActivityEvent | string | null;
}

const SEARCH_TOOLS = new Set(["nearest_nodes", "find_nodes", "search_fulltext"]);
const FETCH_TOOLS = new Set(["get_node", "get_neighbors", "traverse"]);
const DRAFT_TOOLS = new Set(["write_node", "edit_node"]);
const ANALYZE_TOOLS = new Set(["find_dupes", "find_orphans", "coverage_summary"]);

export function BusyIndicator({ activity }: BusyIndicatorProps) {
  const tag = typeof activity === "string" ? activity : activityTagFromEvent(activity);

  return (
    <div
      aria-label={`Bigweld is ${tag}`}
      className="mx-4 flex items-center gap-2 text-sm text-muted-foreground"
      data-testid="busy-indicator"
      role="status"
    >
      <CogIcon
        aria-hidden="true"
        className="size-4 animate-spin text-hpe-brand"
        style={{ animationDuration: "900ms" }}
      />
      <span className="rounded-sm border border-hpe-brand/30 bg-hpe-brand/10 px-2 py-0.5 text-foreground text-xs">
        {tag}
      </span>
    </div>
  );
}

export function activityTagFromEvent(activity?: ActivityEvent | null): string {
  if (activity?.type === "reasoning") return "thinking";

  const toolName = normalizeToolName(activity?.toolName);
  if (!toolName) return "working";

  if (SEARCH_TOOLS.has(toolName)) return "searching the graph";
  if (FETCH_TOOLS.has(toolName)) return `fetching ${extractLabel(activity)}`;
  if (DRAFT_TOOLS.has(toolName)) return "drafting";
  if (toolName === "delete_node") return "removing";
  if (ANALYZE_TOOLS.has(toolName)) return "analyzing";
  if (toolName === "patch_artifact") return "updating artifact";

  return "working";
}

export function activityTagFromToolCall(toolCall: unknown): string {
  if (!toolCall || typeof toolCall !== "object") return "working";

  const value = toolCall as {
    toolName?: string;
    tool_name?: string;
    type?: string;
    input?: unknown;
    args?: unknown;
  };
  return activityTagFromEvent({
    type: "tool",
    toolName: value.toolName ?? value.tool_name ?? value.type,
    input: value.input ?? value.args,
  });
}

function normalizeToolName(toolName: string | null | undefined): string {
  return (toolName ?? "")
    .replace(/^tool-/, "")
    .replace(/^dynamic-tool-/, "")
    .toLowerCase()
    .replaceAll("-", "_");
}

function extractLabel(activity?: ActivityEvent | null): string {
  if (activity?.label?.trim()) return activity.label.trim();
  const input = activity?.input;
  if (!input || typeof input !== "object") return "node";

  const record = input as Record<string, unknown>;
  for (const key of ["label", "title", "name", "id", "node_id"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }

  return "node";
}
