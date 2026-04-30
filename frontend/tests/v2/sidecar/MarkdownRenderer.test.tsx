import { render, screen } from "@testing-library/react";
import { codeToHtml } from "shiki";
import { describe, expect, it, vi } from "vitest";
import { MarkdownRenderer } from "@/v2/components/sidecar/MarkdownRenderer";

vi.mock("shiki", () => ({
  codeToHtml: vi.fn(async (code: string) => `<pre class="shiki"><code>${code}</code></pre>`),
}));

describe("MarkdownRenderer", () => {
  it("renders markdown tables and shiki-highlighted code blocks", async () => {
    render(
      <MarkdownRenderer
        body={[
          "# Artifact",
          "",
          "| A | B |",
          "|---|---|",
          "| one | two |",
          "",
          "```ts",
          "const x = 1",
          "```",
        ].join("\n")}
      />,
    );

    expect(screen.getByRole("heading", { name: "Artifact" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "A" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "two" })).toBeInTheDocument();
    expect(await screen.findByTestId("markdown-renderer")).toBeInTheDocument();
    expect(codeToHtml).toHaveBeenCalledWith(
      "const x = 1",
      expect.objectContaining({ lang: "ts" }),
    );
  });
});
