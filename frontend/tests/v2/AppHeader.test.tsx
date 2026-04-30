import { screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppHeader } from "@/v2/components/header/AppHeader";
import { useChatStore } from "@/v2/stores/chatStore";
import { renderWithProviders } from "./test-utils";

describe("v2 AppHeader", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useChatStore.getState().resetConversation();
    useChatStore.getState().setMessageCount(2);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("composes HPE logo, Bigweld wordmark, ContextBar, Compact, and theme toggle", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          tokens_used: 500,
          token_limit: 50_000,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    renderWithProviders(<AppHeader />);

    expect(screen.getByAltText("HPE")).toBeInTheDocument();
    expect(screen.getByText("Bigweld")).toBeInTheDocument();
    expect(await screen.findByText("500 / 50,000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compact conversation" })).toBeEnabled();
    expect(screen.getByRole("button", { name: /switch to light mode/i })).toBeInTheDocument();
  });
});
