import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SpreadsheetRenderer } from "@/v2/components/sidecar/SpreadsheetRenderer";

describe("SpreadsheetRenderer", () => {
  it("renders CSV rows with sortable columns", () => {
    render(<SpreadsheetRenderer body={"Name,Score\nAlpha,10\nBeta,2\n"} />);

    expect(screen.getByRole("columnheader", { name: /name/i })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Alpha" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /score/i }));

    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByRole("cell", { name: "Beta" })).toBeInTheDocument();
    expect(within(rows[2]).getByRole("cell", { name: "Alpha" })).toBeInTheDocument();
  });
});

