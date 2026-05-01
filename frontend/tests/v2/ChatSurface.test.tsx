import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatSurface } from "@/v2/components/chat/ChatSurface";
import { useChatStore } from "@/v2/stores/chatStore";
import { renderWithProviders } from "./test-utils";

const encoder = new TextEncoder();

describe("v2 ChatSurface", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useChatStore.getState().resetConversation();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders text deltas as the SSE stream is consumed", async () => {
    let controller: ReadableStreamDefaultController<Uint8Array>;
    const stream = new ReadableStream<Uint8Array>({
      start: (streamController) => {
        controller = streamController;
      },
    });

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: {
          "content-type": "text/event-stream",
          "x-vercel-ai-ui-message-stream": "v1",
        },
      }),
    );

    renderWithProviders(<ChatSurface />);

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "fake message" },
    });
    fireEvent.click(screen.getByLabelText("Send message"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls[0][0]).toBe("/chat");

    await act(async () => {
      controller.enqueue(
        encoder.encode(
          [
            sse({ type: "start", messageId: "assistant-1" }),
            sse({ type: "text-start", id: "text-1" }),
            sse({ type: "text-delta", id: "text-1", delta: "Hello" }),
          ].join(""),
        ),
      );
    });

    expect(await screen.findByText("Hello")).toBeInTheDocument();

    await act(async () => {
      controller.enqueue(
        encoder.encode(
          [
            sse({ type: "text-delta", id: "text-1", delta: " world" }),
            sse({ type: "text-end", id: "text-1" }),
            sse({ type: "finish", finishReason: "stop" }),
          ].join(""),
        ),
      );
      controller.close();
    });

    expect(await screen.findByText("Hello world")).toBeInTheDocument();
  });
});

function sse(value: Record<string, unknown>): string {
  return `data: ${JSON.stringify(value)}\n\n`;
}
