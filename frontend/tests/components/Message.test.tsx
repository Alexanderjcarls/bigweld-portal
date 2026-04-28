import { beforeEach, describe, it, expect } from "vitest";
import { Profiler } from "react";
import { act, render, screen } from "@testing-library/react";
import { Message } from "@/components/chat/Message";
import { useChatStore } from "@/stores/chatStore";

describe("Message", () => {
  beforeEach(() => {
    useChatStore.getState().reset();
  });

  it("renders user message text", () => {
    useChatStore.getState().loadMessages([
      {
        id: "msg-user",
        role: "user",
        blocks: [{ kind: "text", text: "hello Bigweld" }],
        ts: new Date().toISOString(),
        isStreaming: false,
      },
    ]);

    render(<Message id="msg-user" />);

    expect(screen.getByText("hello Bigweld")).toBeInTheDocument();
  });

  it("does not rerender sibling messages when one message changes", () => {
    useChatStore.getState().loadMessages([
      {
        id: "msg-a",
        role: "assistant",
        blocks: [{ kind: "text", text: "alpha" }],
        ts: new Date().toISOString(),
        isStreaming: true,
      },
      {
        id: "msg-b",
        role: "assistant",
        blocks: [{ kind: "text", text: "bravo" }],
        ts: new Date().toISOString(),
        isStreaming: true,
      },
    ]);
    let msgAUpdates = 0;
    let msgBUpdates = 0;

    render(
      <>
        <Profiler id="msg-a" onRender={() => { msgAUpdates += 1; }}>
          <Message id="msg-a" />
        </Profiler>
        <Profiler id="msg-b" onRender={() => { msgBUpdates += 1; }}>
          <Message id="msg-b" />
        </Profiler>
      </>,
    );
    msgAUpdates = 0;
    msgBUpdates = 0;

    act(() => {
      useChatStore.getState().appendToCurrentTextBlock("msg-b", "!");
    });

    expect(msgAUpdates).toBe(0);
    expect(msgBUpdates).toBeGreaterThan(0);
  });
});
