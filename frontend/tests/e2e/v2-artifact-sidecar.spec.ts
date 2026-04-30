import { expect, test, type Page, type Route } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";
const CONV_ID = "11111111-1111-4111-8111-111111111111";

test("v2 artifact sidecar lifecycle: create, mutate, navigate, pull, close", async ({ page }) => {
  const state = installArtifactRoutes(page);

  await page.addInitScript((conversationId) => {
    window.localStorage.setItem("bigweld-v2-conversation-id", conversationId);
  }, CONV_ID);

  await page.goto(`${BASE}/v2/`);

  const dataTransfer = await page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    transfer.items.add(
      new File(["# Uploaded\n\nOriginal body."], "uploaded.md", {
        type: "text/markdown",
      }),
    );
    return transfer;
  });

  const chatSurface = page.getByTestId("chat-surface");
  await chatSurface.dispatchEvent("dragenter", { dataTransfer });
  await expect(page.getByTestId("artifact-sidecar")).toBeVisible();
  await expect(page.getByTestId("artifact-drop-zone")).toBeVisible();

  await chatSurface.dispatchEvent("drop", { dataTransfer });
  await expect(page.getByText("uploaded.md")).toBeVisible();
  await expect(page.getByText("Original body.")).toBeVisible();

  await page.getByRole("textbox", { name: "Message" }).fill("revise the artifact");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("Updated body.")).toBeVisible();

  await page.getByLabel("Previous artifact version").click();
  await expect(page.getByText("Original body.")).toBeVisible();
  await page.getByLabel("Next artifact version").click();
  await expect(page.getByText("Updated body.")).toBeVisible();

  await page.getByRole("button", { name: "Pull artifact" }).click();
  await expect(page.getByRole("dialog", { name: "Browse artifacts" })).toBeVisible();
  await page
    .getByRole("listitem")
    .filter({ hasText: "Global report" })
    .getByRole("button", { name: "Pull" })
    .click();
  await expect(page.getByText("Global report")).toBeVisible();
  await expect(page.getByText("Pulled body.")).toBeVisible();
  expect(state.pulledArtifactCreated).toBe(true);

  await page.getByLabel("Close artifact sidecar").click();
  await expect(page.getByTestId("artifact-sidecar")).toBeHidden();
});

function installArtifactRoutes(page: Page) {
  const droppedV1 = {
    id: "artifact-drop",
    conv_id: CONV_ID,
    type: "markdown",
    title: "uploaded.md",
    source: "user_dropped",
    current_version: 1,
    version: 1,
    body: "# Uploaded\n\nOriginal body.",
  };
  const droppedV2 = {
    ...droppedV1,
    current_version: 2,
    version: 2,
    body: "# Uploaded\n\nUpdated body.",
  };
  const droppedV1AfterMutation = {
    ...droppedV1,
    current_version: 2,
  };
  const globalArtifact = {
    id: "global-report",
    conv_id: "22222222-2222-4222-8222-222222222222",
    type: "markdown",
    title: "Global report",
    source: "bigweld",
    current_version: 1,
    version: 1,
    body: "# Global report\n\nPulled body.",
  };
  const pulledArtifact = {
    ...globalArtifact,
    id: "pulled-report",
    conv_id: CONV_ID,
    source: "cross_conv_pulled",
  };
  const state = {
    currentDropped: droppedV1,
    pulledArtifactCreated: false,
  };

  page.route("**/api/conversations**", (route) =>
    route.fulfill({
      contentType: "application/json",
      json: { conversations: [] },
    }),
  );

  page.route("**/api/context-stats**", (route) =>
    route.fulfill({
      contentType: "application/json",
      json: { context_window_pct: 0, context_window_total: 50000, tokens_used: 0 },
    }),
  );

  page.route("**/chat", (route) => {
    state.currentDropped = droppedV2;
    return route.fulfill({
      body: [
        sse({ type: "start", messageId: "assistant-1" }),
        sse({ type: "text-start", id: "text-1" }),
        sse({
          type: "text-delta",
          id: "text-1",
          delta: "Updated @artifact:artifact-drop",
        }),
        sse({ type: "text-end", id: "text-1" }),
        sse({ type: "finish", finishReason: "stop" }),
      ].join(""),
      headers: {
        "content-type": "text/event-stream",
        "x-vercel-ai-ui-message-stream": "v1",
      },
      status: 200,
    });
  });

  page.route("**/api/artifacts**", async (route) => {
    await handleArtifactRoute(route, {
      droppedV1,
      droppedV1AfterMutation,
      globalArtifact,
      pulledArtifact,
      state,
    });
  });

  return state;
}

async function handleArtifactRoute(
  route: Route,
  fixtures: {
    droppedV1: Record<string, unknown>;
    droppedV1AfterMutation: Record<string, unknown>;
    globalArtifact: Record<string, unknown>;
    pulledArtifact: Record<string, unknown>;
    state: {
      currentDropped: Record<string, unknown>;
      pulledArtifactCreated: boolean;
    };
  },
) {
  const request = route.request();
  const url = new URL(request.url());
  const path = url.pathname;

  if (request.method() === "POST") {
    const contentType = request.headers()["content-type"] ?? "";
    const body = contentType.includes("application/json")
      ? (request.postDataJSON() as { source?: string } | null)
      : null;
    if (body?.source === "cross_conv_pulled") {
      fixtures.state.pulledArtifactCreated = true;
      await route.fulfill({ contentType: "application/json", json: fixtures.pulledArtifact, status: 201 });
      return;
    }

    fixtures.state.currentDropped = fixtures.droppedV1;
    await route.fulfill({ contentType: "application/json", json: fixtures.droppedV1, status: 201 });
    return;
  }

  if (path.endsWith("/artifact-drop/versions/1")) {
    await route.fulfill({ contentType: "application/json", json: fixtures.droppedV1AfterMutation });
    return;
  }

  if (path.endsWith("/artifact-drop")) {
    await route.fulfill({ contentType: "application/json", json: fixtures.state.currentDropped });
    return;
  }

  if (url.searchParams.get("global") === "true") {
    await route.fulfill({
      contentType: "application/json",
      json: { artifacts: [fixtures.globalArtifact, fixtures.state.currentDropped] },
    });
    return;
  }

  await route.fulfill({
    contentType: "application/json",
    json: { artifacts: [fixtures.state.currentDropped] },
  });
}

function sse(value: Record<string, unknown>): string {
  return `data: ${JSON.stringify(value)}\n\n`;
}
