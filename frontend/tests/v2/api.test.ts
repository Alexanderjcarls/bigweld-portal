import { afterEach, describe, expect, it, vi } from "vitest";
import { getV2Conversation } from "@/v2/lib/api";

describe("v2 api helpers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("normalizes backend conversation detail responses", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "conv-1",
          title: "Case work",
          started_at: "2026-05-01T00:00:00.000Z",
          last_active_at: "2026-05-01T01:00:00.000Z",
          archived: false,
          messages: [{ id: "m1", role: "user", content: "hello" }],
          compacted_summaries: [{ id: 1, summary: "short" }],
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );

    const detail = await getV2Conversation("conv-1");

    expect(detail.conversation).toMatchObject({
      id: "conv-1",
      title: "Case work",
      last_active_at: "2026-05-01T01:00:00.000Z",
    });
    expect(detail.messages).toEqual([{ id: "m1", role: "user", content: "hello" }]);
    expect(detail.active_compacted_summaries).toEqual([{ id: 1, summary: "short" }]);
  });
});
