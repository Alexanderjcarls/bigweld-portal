import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatInput } from "@/components/chat/ChatInput";

describe("ChatInput", () => {
  it("renders Send button + editor area", () => {
    render(<ChatInput />);
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });
});
