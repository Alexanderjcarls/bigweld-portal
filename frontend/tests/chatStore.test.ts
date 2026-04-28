import { afterEach, describe, expect, it } from "vitest";
import { useChatStore } from "@/stores/chatStore";

describe("chatStore block accumulators", () => {
  afterEach(() => {
    useChatStore.getState().reset();
  });

  it("appendToCurrentTextBlock creates a text block when the last block is non-text", () => {
    const assistantId = useChatStore.getState().startUserTurn("hi");
    useChatStore.getState().beginAssistantBlock(assistantId, {
      kind: "tool_use",
      id: "tool-1",
      name: "Bash",
      input: {},
      isStreaming: true,
    });

    useChatStore.getState().appendToCurrentTextBlock(assistantId, "done");

    const assistant = useChatStore.getState().messages.find(message => message.id === assistantId);
    expect(assistant?.blocks).toEqual([
      { kind: "tool_use", id: "tool-1", name: "Bash", input: {}, isStreaming: true },
      { kind: "text", text: "done" },
    ]);
  });

  it("appendToolUseInput accumulates partial JSON until finalizeToolUse", () => {
    const assistantId = useChatStore.getState().startUserTurn("run this");
    useChatStore.getState().beginAssistantBlock(assistantId, {
      kind: "tool_use",
      id: "tool-2",
      name: "Bash",
      input: {},
      isStreaming: true,
    });

    useChatStore.getState().appendToolUseInput(assistantId, "tool-2", "{\"command\":\"ec");
    useChatStore.getState().appendToolUseInput(assistantId, "tool-2", "ho hi\"}");
    useChatStore.getState().finalizeToolUse(assistantId, "tool-2", "hi");

    const assistant = useChatStore.getState().messages.find(message => message.id === assistantId);
    expect(assistant?.blocks[0]).toEqual({
      kind: "tool_use",
      id: "tool-2",
      name: "Bash",
      input: { command: "echo hi" },
      output: "hi",
      error: undefined,
      isStreaming: false,
    });
  });

  it("loadMessages ignores stale hydration after an active turn starts", async () => {
    useChatStore.getState().setConversationId("conv-a");
    const hydration = Promise.resolve([
      {
        id: "old-msg",
        role: "user" as const,
        blocks: [{ kind: "text" as const, text: "old" }],
        ts: new Date().toISOString(),
        isStreaming: false,
      },
    ]).then(messages => {
      useChatStore.getState().loadMessages(messages, "conv-a");
    });

    useChatStore.getState().setConversationId("conv-b");
    useChatStore.getState().startUserTurn("new turn");
    await hydration;

    expect(useChatStore.getState().messages[0].blocks).toEqual([
      { kind: "text", text: "new turn" },
    ]);
  });
});
