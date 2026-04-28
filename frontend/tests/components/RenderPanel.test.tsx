import { beforeEach, describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RenderPanel } from "@/components/workspace/RenderPanel";
import { useWorkspaceStore } from "@/stores/workspaceStore";

describe("RenderPanel", () => {
  beforeEach(() => {
    useWorkspaceStore.getState().clear();
  });

  it("sanitizes rendered SVG before injection", () => {
    useWorkspaceStore.getState().setSource("mermaid", "graph TD; A-->B");
    useWorkspaceStore.getState().setRenderedSvg(
      '<svg><script>alert(1)</script><circle onload="alert(2)" cx="1" cy="1" r="1"></circle></svg>',
    );

    const { container } = render(<RenderPanel />);

    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(container.querySelector("script")).not.toBeInTheDocument();
    expect(container.innerHTML).not.toContain("onload");
  });
});
