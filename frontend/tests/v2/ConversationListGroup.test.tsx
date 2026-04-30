import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConversationListGroup } from "@/v2/components/conversations/ConversationListGroup";
import type { ConversationSummary } from "@/v2/lib/api";

describe("v2 ConversationListGroup", () => {
  it("renders bucket heading and conversation items", () => {
    const conversations: ConversationSummary[] = [
      {
        id: "conv-a",
        title: "Alpha",
        started_at: new Date().toISOString(),
        last_active_at: new Date().toISOString(),
        artifact_count: 0,
      },
    ];

    render(
      <ConversationListGroup
        activeConversationId="conv-a"
        bucket="Today"
        conversations={conversations}
        onArchive={() => undefined}
        onRename={() => undefined}
        onSelect={() => undefined}
      />,
    );

    expect(screen.getByRole("heading", { name: "Today" })).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Alpha").closest("button")).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
