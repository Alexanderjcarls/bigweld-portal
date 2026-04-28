import { describe, expect, it } from "vitest";
import { eventsToMessages } from "@/components/chat/ChatSurface";

describe("eventsToMessages", () => {
  it("lets persisted assistant blocks replace reconstructed tool placeholders", () => {
    const messages = eventsToMessages([
      { type: "user", content: "run it", ts: "2026-04-28T00:00:00Z" },
      {
        type: "tool_use_result",
        tool: "Bash",
        input: { command: "printf ok" },
        output: { stdout: "ok", stderr: "" },
        ts: "2026-04-28T00:00:01Z",
      },
      {
        type: "assistant",
        blocks: [
          { kind: "text", text: "pre" },
          {
            kind: "tool_use",
            id: "toolu_1",
            name: "Bash",
            input: { command: "printf ok" },
            output: "ok",
          },
          { kind: "text", text: "post" },
        ],
        content: "prepost",
        ts: "2026-04-28T00:00:02Z",
      },
    ]);

    expect(messages).toHaveLength(2);
    expect(messages[1].blocks).toEqual([
      { kind: "text", text: "pre" },
      {
        kind: "tool_use",
        id: "toolu_1",
        name: "Bash",
        input: { command: "printf ok" },
        output: "ok",
        error: undefined,
        isStreaming: false,
      },
      { kind: "text", text: "post" },
    ]);
  });
});
