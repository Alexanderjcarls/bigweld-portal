import { expect, test } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";

test("v2 AppHeader composition", async ({ page }) => {
  await page.route("**/api/context-stats**", async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        "access-control-allow-origin": "*",
        "content-type": "application/json",
      },
      body: JSON.stringify({ tokens_used: 2500, token_limit: 50_000 }),
    });
  });
  await page.route("**/api/conversations**", async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        "access-control-allow-origin": "*",
        "content-type": "application/json",
      },
      body: JSON.stringify({ conversations: [] }),
    });
  });

  await page.goto(new URL("/v2/", BASE).toString());

  const header = page.getByTestId("v2-app-header");
  await expect(header.getByAltText("HPE")).toBeVisible();
  await expect(header.getByText("Bigweld")).toBeVisible();
  await expect(header.getByText("Context")).toBeVisible();
  await expect(header.getByText("2,500 / 50,000")).toBeVisible();
  await expect(header.getByRole("button", { name: "Compact conversation" })).toBeVisible();
  await expect(header.getByRole("button", { name: /switch to light mode/i })).toBeVisible();
});
