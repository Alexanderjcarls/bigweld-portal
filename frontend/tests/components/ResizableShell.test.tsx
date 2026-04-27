import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResizableShell } from "@/components/layout/ResizableShell";

describe("ResizableShell", () => {
  it("renders all three slots", () => {
    render(
      <ResizableShell
        chat={<div data-testid="chat-slot">CHAT</div>}
        workspace={<div data-testid="ws-slot">WS</div>}
        download={<div data-testid="dl-slot">DL</div>}
      />
    );
    expect(screen.getByTestId("chat-slot")).toBeInTheDocument();
    expect(screen.getByTestId("ws-slot")).toBeInTheDocument();
    expect(screen.getByTestId("dl-slot")).toBeInTheDocument();
  });
});
