import { beforeEach, describe, expect, it } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { useFenceDetector } from "@/hooks/useFenceDetector";
import { useChatStore } from "@/stores/chatStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";

function Harness() {
  useFenceDetector();
  return null;
}

describe("useFenceDetector", () => {
  beforeEach(() => {
    useChatStore.getState().reset();
    useWorkspaceStore.getState().clear();
  });

  it("uses the last fenced diagram without regex state leakage", async () => {
    useChatStore.getState().loadMessages([
      {
        id: "assistant",
        role: "assistant",
        blocks: [{
          kind: "text",
          text: "```mermaid\ngraph TD; A-->B\n```\n```d2\na -> b\n```",
        }],
        ts: new Date().toISOString(),
        isStreaming: false,
      },
    ]);

    render(<Harness />);

    await waitFor(() => {
      expect(useWorkspaceStore.getState().current).toMatchObject({
        type: "d2",
        source: "a -> b",
      });
    });
  });
});
