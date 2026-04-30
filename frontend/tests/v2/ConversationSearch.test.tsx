import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConversationSearch } from "@/v2/components/conversations/ConversationSearch";

describe("v2 ConversationSearch", () => {
  it("emits title-substring filter changes", () => {
    const onChange = vi.fn();

    render(<ConversationSearch onChange={onChange} value="" />);

    fireEvent.change(screen.getByLabelText("Filter conversations"), {
      target: { value: "case" },
    });

    expect(onChange).toHaveBeenCalledWith("case");
  });
});
