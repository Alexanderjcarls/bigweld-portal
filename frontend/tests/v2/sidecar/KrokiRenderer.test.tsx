import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { KrokiRenderer } from "@/v2/components/sidecar/KrokiRenderer";

describe("KrokiRenderer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("posts diagram source to Kroki and renders returned SVG", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("<svg><title>diagram</title></svg>", { status: 200 }),
    );

    render(<KrokiRenderer kind="mermaid" source={"graph TD\nA-->B"} />);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "http://192.168.0.30:8889/mermaid/svg",
        expect.objectContaining({
          body: "graph TD\nA-->B",
          method: "POST",
        }),
      ),
    );
    expect(await screen.findByText("diagram")).toBeInTheDocument();
  });
});
