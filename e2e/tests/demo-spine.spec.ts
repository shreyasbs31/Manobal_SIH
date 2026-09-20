import { expect, test } from "@playwright/test";

import { signIn } from "./session";

const engine = process.env.ENGINE_URL ?? "http://localhost:8000";

async function reset(request: { post: (url: string, opts: { data?: object; headers?: Record<string, string> }) => Promise<{ json: () => Promise<{ seconds?: number; access_token?: string }> }> }) {
  const login = await request.post(`${engine}/api/v1/auth/demo-login`, {
    data: { role: "director" },
  });
  const body = (await login.json()) as { access_token: string };
  const result = await request.post(`${engine}/api/v1/demo/reset`, {
    headers: { authorization: `Bearer ${body.access_token}` },
  });
  const payload = (await result.json()) as { seconds: number };
  expect(payload.seconds).toBeLessThan(20);
}

async function runSpine(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Support, not surveillance.")).toBeVisible();
  await expect(page.locator("#ps-map")).toBeVisible();

  await signIn(page, "personnel", "arjun");
  await page.goto("/app/onboarding");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();

  await page.goto("/app/check-in");
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();

  await signIn(page, "uwo");
  await page.goto("/welfare");
  await expect(page.getByText("MB-4091").first()).toBeVisible();
  await page.goto("/welfare/cases/MB-4091");
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

  await signIn(page, "mo");
  await page.goto("/medical");
  await expect(page.getByText("MB-6604").first()).toBeVisible();

  await signIn(page, "wdec");
  await page.goto("/governance");
  await expect(page.getByRole("heading", { name: "Audit chain" })).toBeVisible();
  await page.getByRole("button", { name: "Tamper" }).click();
  await expect(page.getByText(/broken|Restore/i).first()).toBeVisible();
  await page.getByRole("button", { name: "Restore" }).click();
  await page.getByRole("button", { name: "Always on" }).click();
  await expect(page.getByText(/acute path cannot/i)).toBeVisible();

  await page.goto("/lab");
  await expect(page.getByText(/Imran stays T1/)).toBeVisible();
  await expect(page.getByText(/Thomas stays T0/)).toBeVisible();
  await page.getByRole("button", { name: "Shifted world" }).click();
  await expect(page.getByText("These figures are from synthetic worlds.")).toBeVisible();

  await signIn(page, "dpo");
  await page.goto("/dpo");
  await expect(page.getByText("erasure").first()).toBeVisible();

  await signIn(page, "hrms_integrator");
  await page.goto("/integrations");
  await expect(page.getByText(/quarantine/i).first()).toBeVisible();

  await page.goto("/architecture");
  await expect(page.getByRole("heading", { name: "Phone" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Never connected" })).toBeVisible();

  await page.goto("/trust");
  await expect(page.getByRole("button", { name: "Read this page aloud" })).toBeVisible();

  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=workspace");
  await expect(page.locator(".mb-stage-drawer")).toBeHidden();
  await expect(page.getByText("Case workspace reveal")).toBeVisible();
}

test("demo spine twice with reset between", async ({ page, request }) => {
  test.setTimeout(240_000);
  if (process.env.AZURE_WEB_URL) {
    test.info().annotations.push({ type: "target", description: process.env.AZURE_WEB_URL });
  }
  await reset(request);
  await runSpine(page);
  await reset(request);
  await runSpine(page);
});

test("azure demo spine twice", async ({ page, request }) => {
  test.setTimeout(240_000);
  test.skip(!process.env.AZURE_WEB_URL, "31.1 no Azure URL in this environment");
  await reset(request);
  await runSpine(page);
  await reset(request);
  await runSpine(page);
});
