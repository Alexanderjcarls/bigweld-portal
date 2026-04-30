import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConversationSidebar } from "@/v2/components/conversations/ConversationSidebar";
import { useChatStore } from "@/v2/stores/chatStore";
import { renderWithProviders } from "./test-utils";

describe("v2 ConversationSidebar", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useChatStore.getState().resetConversation();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("groups conversations, filters by title, and loads a selected conversation", async () => {
    const today = new Date().toISOString();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/conversations/conv-1")) {
        return jsonResponse({
          messages: [
            {
              id: "m1",
              role: "user",
              content: "Show me the case",
            },
          ],
        });
      }

      return jsonResponse({
        conversations: [
          {
            id: "conv-1",
            title: "Case review",
            started_at: today,
            last_active_at: today,
            artifact_count: 2,
          },
          {
            id: "conv-2",
            title: "Migration notes",
            started_at: "2020-01-01T00:00:00.000Z",
            last_active_at: "2020-01-01T00:00:00.000Z",
            artifact_count: 0,
          },
        ],
      });
    });

    renderWithProviders(<ConversationSidebar />);

    expect(await screen.findByRole("heading", { name: "Today" })).toBeInTheDocument();
    expect(screen.getByText("Case review")).toBeInTheDocument();
    expect(screen.getByText("Migration notes")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Filter conversations"), {
      target: { value: "case" },
    });

    expect(screen.getByText("Case review")).toBeInTheDocument();
    expect(screen.queryByText("Migration notes")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Case review"));

    await waitFor(() => {
      expect(useChatStore.getState().conversationId).toBe("conv-1");
      expect(useChatStore.getState().hydratedMessages?.[0]?.parts[0]).toEqual({
        type: "text",
        text: "Show me the case",
      });
    });
    expect(fetchMock).toHaveBeenCalled();
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
