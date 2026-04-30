import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ToolCall } from "@/v2/components/chat/ToolCall";

describe("v2 ToolCall", () => {
  it("renders completed tool calls collapsed by default", () => {
    render(
      <ToolCall
        part={{
          type: "tool-web_search",
          toolCallId: "tool-1",
          state: "output-available",
          input: { query: "bigweld" },
          output: { ok: true },
        }}
      />,
    );

    expect(screen.getByText("web_search")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.queryByText("Result")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("web_search"));

    expect(screen.getByText("Result")).toBeInTheDocument();
  });

  it("auto-expands errored tool calls", () => {
    render(
      <ToolCall
        part={{
          type: "tool-bash",
          toolCallId: "tool-2",
          state: "output-error",
          input: { command: "false" },
          errorText: "command failed",
        }}
      />,
    );

    expect(screen.getByText("bash")).toBeInTheDocument();
    expect(screen.getAllByText("Error")).toHaveLength(2);
    expect(screen.getByText("View Error")).toBeInTheDocument();
  });
});
