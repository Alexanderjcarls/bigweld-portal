import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConversationItem } from "@/v2/components/conversations/ConversationItem";
import type { ConversationSummary } from "@/v2/lib/api";

const conversation: ConversationSummary = {
  id: "12345678-1234-1234-1234-123456789abc",
  title: "Case routing",
  started_at: new Date().toISOString(),
  last_active_at: new Date().toISOString(),
  artifact_count: 3,
};

describe("v2 ConversationItem", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders title, relative time, artifact badge, and select action", () => {
    const onSelect = vi.fn();

    render(
      <ConversationItem
        conversation={conversation}
        onArchive={() => undefined}
        onRename={() => undefined}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("Case routing")).toBeInTheDocument();
    expect(screen.getByText("just now")).toBeInTheDocument();
    expect(screen.getByLabelText("3 artifacts")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Case routing"));

    expect(onSelect).toHaveBeenCalledWith(conversation.id);
  });

  it("opens rename/archive actions from the context menu", async () => {
    const onRename = vi.fn();
    const onArchive = vi.fn();
    vi.spyOn(window, "prompt").mockReturnValue("Renamed");

    render(
      <ConversationItem
        conversation={conversation}
        onArchive={onArchive}
        onRename={onRename}
        onSelect={() => undefined}
      />,
    );

    fireEvent.contextMenu(screen.getByText("Case routing"));
    fireEvent.click(await screen.findByText("Rename"));

    await waitFor(() => expect(onRename).toHaveBeenCalledWith(conversation.id, "Renamed"));

    fireEvent.contextMenu(screen.getByText("Case routing"));
    fireEvent.click(await screen.findByText("Archive"));

    expect(onArchive).toHaveBeenCalledWith(conversation.id);
  });
});
