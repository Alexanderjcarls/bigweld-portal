import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CompactModal } from "@/v2/components/header/CompactModal";
import { renderWithProviders } from "./test-utils";

describe("v2 CompactModal", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("runs preview then confirm against compact endpoints", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        jsonResponse({
          proposed_summary: "Condensed conversation summary",
          diff_preview: "- original\n+ summary",
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ ok: true, summary_id: 42 }));

    renderWithProviders(
      <CompactModal
        conversationId="conv-1"
        onOpenChange={() => undefined}
        open
        rangeEndIdx={4}
        rangeStartIdx={0}
      />,
    );

    expect(await screen.findByText("Condensed conversation summary")).toBeInTheDocument();
    expect(screen.getByText("- original + summary")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirm compact" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(String(fetchMock.mock.calls[0][0])).toBe("/api/compact");
    expect(String(fetchMock.mock.calls[1][0])).toBe("/api/compact/confirm");
    expect(await screen.findByText("Compact summary persisted.")).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
