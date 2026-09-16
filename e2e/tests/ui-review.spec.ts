import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const screens = [
  ["landing", "/"],
  ["home", "/app"],
  ["check-in", "/app/check-in"],
  ["saathi", "/app/saathi"],
  ["safety", "/app/safety"],
  ["breathing", "/app/toolkit/breathe"],
  ["me", "/app/me"],
  ["welfare", "/welfare"],
  ["case", "/welfare/cases/MB-4091"],
  ["medical", "/medical"],
  ["command", "/command"],
  ["governance", "/governance"],
  ["architecture", "/architecture"],
  ["stage", "/stage"],
] as const;

const personas = ["MB-4091", "MB-6604", "MB-2217"] as const;

for (const [slug, route] of screens) {
  test(`axe ${slug}`, async ({ page }) => {
    test.setTimeout(90_000);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(route, { waitUntil: "domcontentloaded" });
    const builder = new AxeBuilder({ page });
    if (slug === "stage") {
      await page.setViewportSize({ width: 1920, height: 1080 });
      builder.exclude("iframe");
    }
    const results = await builder.analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test("persona tokens appear on fixture screens", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/app");
  await expect(page.getByText("Suprabhat, Arjun")).toBeVisible();
  await page.goto("/welfare");
  for (const id of personas) {
    await expect(page.getByText(id).first()).toBeVisible();
  }
  await page.goto("/welfare/cases/MB-4091");
  await expect(page.getByText("MB-4091").first()).toBeVisible();
  await page.goto("/medical");
  await expect(page.getByText("MB-6604").first()).toBeVisible();
  await page.goto("/command");
  await expect(page.getByText("Charlie Coy's workload has risen for three weeks.")).toBeVisible();
  await expect(page.getByText("MB-4091")).toHaveCount(0);
});

test("stage drawer is hidden until toggled", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/stage", { waitUntil: "domcontentloaded" });
  await expect(page.locator(".mb-stage-drawer")).toBeHidden();
  await page.locator(".mb-stage-bar").click();
  await page.keyboard.press("d");
  await expect(page.locator(".mb-stage-drawer")).toBeVisible();
});
