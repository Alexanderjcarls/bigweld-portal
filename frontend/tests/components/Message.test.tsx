import { beforeEach, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
});
