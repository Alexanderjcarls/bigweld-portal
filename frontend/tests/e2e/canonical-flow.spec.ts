import { test, expect } from "@playwright/test";

const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";

test("canonical flow: new conversation -> send message -> see streaming response", async ({ page }) => {
  await page.goto(BASE);
  await expect(page.getByText(/working space/i)).toBeVisible();
  await page.locator(".ProseMirror").click();
  await page.keyboard.type("hello bigweld");
  await page.getByRole("button", { name: /send/i }).click();
  await expect(page.getByText("hello bigweld")).toBeVisible();
});
