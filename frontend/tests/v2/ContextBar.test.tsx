import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ContextBar } from "@/v2/components/header/ContextBar";
import { dispatchContextStatsChatEvent } from "@/v2/hooks/useContextStats";
import { renderWithProviders } from "./test-utils";

describe("v2 ContextBar", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows token usage from /api/context-stats", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        tokens_used: 12_500,
        token_limit: 50_000,
      }),
    );

    renderWithProviders(<ContextBar conversationId="conv-1" />);

    expect(await screen.findByText("12,500 / 50,000")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "12500");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/context-stats?conv_id=conv-1");
  });

  it("refetches when chat events are dispatched", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse({ tokens_used: 1, token_limit: 50_000 }))
      .mockResolvedValueOnce(jsonResponse({ tokens_used: 2, token_limit: 50_000 }));

    renderWithProviders(<ContextBar conversationId="conv-2" />);

    expect(await screen.findByText("1 / 50,000")).toBeInTheDocument();
    dispatchContextStatsChatEvent();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("2 / 50,000")).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
