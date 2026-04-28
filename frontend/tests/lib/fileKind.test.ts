import { describe, expect, it } from "vitest";
import { classifyFile } from "@/lib/fileKind";

describe("classifyFile", () => {
  it("treats known text MIME types as text", () => {
    const file = new File(["# hi"], "README", { type: "text/markdown" });
    expect(classifyFile(file)).toBe("text");
  });

  it("falls back to known text extensions when MIME is empty", () => {
    const file = new File(["# hi"], "README.md", { type: "" });
    expect(classifyFile(file)).toBe("text");
  });

  it("treats known binary MIME types as binary", () => {
    const file = new File(["%PDF"], "doc.pdf", { type: "application/pdf" });
    expect(classifyFile(file)).toBe("binary");
  });

  it("treats unknown empty-MIME extensions as binary", () => {
    const file = new File(["data"], "payload.xyz", { type: "" });
    expect(classifyFile(file)).toBe("binary");
  });

  it("matches extensions case-insensitively", () => {
    const file = new File(["# hi"], "README.MD", { type: "" });
    expect(classifyFile(file)).toBe("text");
  });
});
