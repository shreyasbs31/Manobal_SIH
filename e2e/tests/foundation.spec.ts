import { expect, test } from "@playwright/test";

const routes = [
  "/",
  "/login",
  "/app",
  "/welfare",
  "/counsel",
  "/medical",
  "/command",
  "/hq",
  "/governance",
  "/dpo",
  "/integrations",
  "/admin",
  "/lab",
  "/trust",
  "/architecture",
  "/director",
  "/stage",
] as const;

const roles = [
  "personnel",
  "uwo",
  "counsellor",
  "mo",
  "commander",
  "hq",
  "wdec",
  "dpo",
  "hrms_integrator",
  "admin",
  "director",
] as const;

const personas = [
  "arjun",
  "meena",
  "imran",
  "thomas",
  "lalit",
  "deepak",
  "rajesh",
  "karthik",
] as const;

for (const route of routes) {
  test(`${route} exposes a synthetic surface`, async ({ page }) => {
    await page.goto(route);
    await expect(page.getByText("Synthetic data").first()).toBeVisible();
  });
}

test("demo login mints every role and persona", async ({ request }) => {
  const engine = process.env.ENGINE_URL ?? "http://localhost:8000";
  for (const role of roles) {
    const response = await request.post(`${engine}/api/v1/auth/demo-login`, {
      data: {
        role,
        persona_id: role === "personnel" ? "arjun" : null,
      },
    });
    expect(response.ok()).toBeTruthy();
  }
  for (const personaId of personas) {
    const response = await request.post(`${engine}/api/v1/auth/demo-login`, {
      data: { role: "personnel", persona_id: personaId },
    });
    expect(response.ok()).toBeTruthy();
  }
});
