import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Reasoning } from "@/v2/components/chat/Reasoning";

describe("v2 Reasoning", () => {
  it("hides empty reasoning", () => {
    const { container } = render(
      <Reasoning part={{ type: "reasoning", text: "", state: "done" }} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("renders non-empty reasoning collapsed by default", () => {
    render(
      <Reasoning
        part={{ type: "reasoning", text: "internal chain", state: "done" }}
      />,
    );

    expect(screen.getByRole("button")).toBeInTheDocument();
    expect(screen.queryByText("internal chain")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByText("internal chain")).toBeInTheDocument();
  });
});
