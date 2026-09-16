import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { roleForRoute, signIn } from "./session";

const screens = [
  ["landing", "/"],
  ["home", "/app"],
  ["onboarding", "/app/onboarding"],
  ["check-in", "/app/check-in"],
  ["saathi", "/app/saathi"],
  ["safety", "/app/safety"],
  ["breathing", "/app/toolkit/breathe"],
  ["toolkit", "/app/toolkit"],
  ["assessments", "/app/assessments"],
  ["rest", "/app/rest"],
  ["talk", "/app/talk"],
  ["buddy", "/app/buddy"],
  ["plan", "/app/plan"],
  ["me", "/app/me"],
  ["welfare", "/welfare"],
  ["case", "/welfare/cases/MB-4091"],
  ["medical", "/medical"],
  ["counsel", "/counsel"],
  ["command", "/command"],
  ["roster", "/command/roster"],
  ["hq", "/hq"],
  ["governance", "/governance"],
  ["dpo", "/dpo"],
  ["integrations", "/integrations"],
  ["admin", "/admin"],
  ["lab", "/lab"],
  ["trust", "/trust"],
  ["architecture", "/architecture"],
  ["director", "/director"],
  ["stage", "/stage"],
] as const;

for (const [slug, route] of screens) {
  test(`axe ${slug}`, async ({ page }) => {
    test.setTimeout(90_000);
    await page.setViewportSize({ width: 1440, height: 900 });
    const session = roleForRoute(route);
    if (session) {
      await signIn(page, session.role, session.persona);
    }
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 45_000 });
    const builder = new AxeBuilder({ page });
    if (slug === "stage") {
      await page.setViewportSize({ width: 1920, height: 1080 });
      builder.exclude("iframe");
    }
    const results = await builder.analyze();
    expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
  });
}

test("live persona tokens appear on signed-in screens", async ({ page }) => {
  test.setTimeout(90_000);
  await signIn(page, "personnel", "arjun");
  await page.goto("/app");
  await expect(page.getByText("Suprabhat, Arjun")).toBeVisible();
  await signIn(page, "uwo");
  await page.goto("/welfare");
  await expect(page.getByText("MB-4091").first()).toBeVisible();
  await page.goto("/welfare/cases/MB-4091");
  await expect(page.getByText("MB-4091").first()).toBeVisible();
  await signIn(page, "mo");
  await page.goto("/medical");
  await expect(page.getByText("MB-6604").first()).toBeVisible();
  await signIn(page, "commander");
  await page.goto("/command");
  await expect(page.getByText("Charlie Coy's workload has risen for three weeks.")).toBeVisible();
  await expect(page.getByText("Post D-7").first()).toBeVisible();
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

test("prompt 7 consoles refuse misuse and export the brief", async ({ page, request }) => {
  test.setTimeout(120_000);
  await signIn(page, "uwo");
  await page.goto("/welfare");
  await expect(page.getByRole("heading", { name: /High/ })).toBeVisible();
  await expect(page.getByText("MB-4091").first()).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/welfare\/cases\/MB-4091/);
  await page.getByLabel("Why you need to reach them").fill("Need to call about rest after duty.");
  await page.getByRole("button", { name: "Reveal to contact" }).click();
  await expect(page.getByText("This person will see that you viewed their identity.")).toBeVisible();

  await signIn(page, "commander");
  await page.goto("/command");
  await expect(page.getByText("Post D-7").first()).toBeVisible();
  await page.getByRole("button", { name: "Open copilot" }).click();
  await page.getByLabel("Question").fill("Charlie Coy mein kaun pareshan hai?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText(/Main kisi jawan ka naam nahi de sakta/)).toBeVisible();
  await expect(page.getByText(/20 se 30/)).toBeVisible();

  await signIn(page, "hq");
  await page.goto("/hq");
  await expect(page.getByRole("heading", { name: "Lever effectiveness" })).toBeVisible();
  await expect(page.getByText("Observational, not causal").first()).toBeVisible();
  const pdf = await request.get("http://localhost:8000/api/v1/hq/brief.pdf", {
    headers: {
      authorization: `Bearer ${await page.evaluate(() => sessionStorage.getItem("manobal.access_token"))}`,
    },
  });
  expect(pdf.ok()).toBeTruthy();
  const body = await pdf.body();
  expect(body.subarray(0, 4).toString()).toBe("%PDF");
});
