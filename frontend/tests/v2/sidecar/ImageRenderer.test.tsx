import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ImageRenderer } from "@/v2/components/sidecar/ImageRenderer";

describe("ImageRenderer", () => {
  it("renders an image artifact from stored file data", () => {
    render(
      <ImageRenderer
        files={{ data_url: "data:image/png;base64,abc123", filename: "chart.png" }}
        title="Chart"
      />,
    );

    const image = screen.getByRole("img", { name: "Chart" });
    expect(image).toHaveAttribute("src", "data:image/png;base64,abc123");
  });
});

