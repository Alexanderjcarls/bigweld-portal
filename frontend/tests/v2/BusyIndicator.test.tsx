import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  activityTagFromEvent,
  activityTagFromToolCall,
  BusyIndicator,
} from "@/v2/components/chat/BusyIndicator";

describe("v2 BusyIndicator", () => {
  it("renders the spinning gear with an activity tag", () => {
    render(<BusyIndicator activity="thinking" />);

    expect(screen.getByRole("status", { name: /thinking/i })).toBeInTheDocument();
    expect(screen.getByText("thinking")).toBeInTheDocument();
  });

  it("maps MCP tool events to user-facing activity tags", () => {
    expect(activityTagFromEvent({ toolName: "nearest_nodes" })).toBe("searching the graph");
    expect(
      activityTagFromEvent({
        toolName: "get_node",
        input: { label: "Case" },
      }),
    ).toBe("fetching Case");
    expect(activityTagFromEvent({ toolName: "patch_artifact" })).toBe(
      "updating artifact",
    );
    expect(activityTagFromEvent({ type: "reasoning" })).toBe("thinking");
    expect(activityTagFromToolCall({ type: "tool-find_dupes" })).toBe("analyzing");
  });
});
