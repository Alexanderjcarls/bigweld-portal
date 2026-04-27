import { describe, it, expect } from "vitest";

describe("frontend scaffold", () => {
  it("env is jsdom", () => {
    expect(typeof window).toBe("object");
    expect(typeof document).toBe("object");
  });

  it("can import react", async () => {
    const React = await import("react");
    expect(React.version).toBeTruthy();
  });
});
