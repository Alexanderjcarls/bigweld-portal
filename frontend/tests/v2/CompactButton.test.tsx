import { fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CompactButton } from "@/v2/components/header/CompactButton";
import { useChatStore } from "@/v2/stores/chatStore";
import { renderWithProviders } from "./test-utils";

describe("v2 CompactButton", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useChatStore.getState().resetConversation();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("is disabled until there are messages to compact", () => {
    renderWithProviders(<CompactButton conversationId="conv-1" messageCount={0} />);

    expect(screen.getByRole("button", { name: "Compact conversation" })).toBeDisabled();
  });

  it("opens the compact modal", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          proposed_summary: "Summary",
          diff_preview: "--- old\n+++ new",
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    renderWithProviders(<CompactButton conversationId="conv-1" messageCount={2} />);

    fireEvent.click(screen.getByRole("button", { name: "Compact conversation" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(await screen.findByText("Summary")).toBeInTheDocument();
  });
});
