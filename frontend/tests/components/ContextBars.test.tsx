import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ContextBars } from "@/components/chat/ContextBars";
import { useChatStore } from "@/stores/chatStore";

describe("ContextBars", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.getState().reset();
  });

  it("renders one context bar from the budget response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        context_window_pct: 12.34,
        context_window_total: 1000000,
      }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    useChatStore.getState().setConversationId("conv-1");

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ContextBars />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("12.3%")).toBeInTheDocument();
    expect(screen.getByText("context")).toBeInTheDocument();
    expect(screen.queryByText("5h Max")).not.toBeInTheDocument();
    expect(screen.queryByText("7d Max")).not.toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/budget?conv_id=conv-1");
  });
});
