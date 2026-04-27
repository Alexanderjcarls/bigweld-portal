import { describe, it, expect } from "vitest";
import { ndjsonReader } from "@/lib/ndjson";

function streamFromChunks(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encoder.encode(chunks[i++]));
      } else {
        controller.close();
      }
    },
  });
}

describe("ndjsonReader", () => {
  it("reads a complete line", async () => {
    const stream = streamFromChunks(['{"a":1}\n']);
    const out: unknown[] = [];
    for await (const ev of ndjsonReader(stream)) out.push(ev);
    expect(out).toEqual([{ a: 1 }]);
  });

  it("handles line split across chunks (#1 bug)", async () => {
    const stream = streamFromChunks(['{"a":', '1}\n']);
    const out: unknown[] = [];
    for await (const ev of ndjsonReader(stream)) out.push(ev);
    expect(out).toEqual([{ a: 1 }]);
  });

  it("skips malformed JSON", async () => {
    const stream = streamFromChunks(["not json\n", '{"a":1}\n']);
    const out: unknown[] = [];
    for await (const ev of ndjsonReader(stream)) out.push(ev);
    expect(out).toEqual([{ a: 1 }]);
  });
});
