import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const base = process.env.WEB_URL ?? "http://localhost:3000";
const engine = process.env.ENGINE_URL ?? "http://localhost:8000";
const outDir = path.resolve("artifacts/ui");
await mkdir(outDir, { recursive: true });

const screens = [
  ["onboarding", "/app/onboarding", "arjun"],
  ["home-arjun", "/app", "arjun"],
  ["home-meena", "/app", "meena"],
  ["home-karthik", "/app", "karthik"],
  ["check-in", "/app/check-in", "arjun"],
  ["saathi", "/app/saathi", "arjun"],
  ["safety", "/app/safety", "arjun"],
  ["toolkit", "/app/toolkit", "arjun"],
  ["assessments", "/app/assessments", "arjun"],
  ["rest", "/app/rest", "meena"],
  ["talk", "/app/talk", "arjun"],
  ["buddy", "/app/buddy", "arjun"],
  ["plan", "/app/plan", "arjun"],
  ["family", "/app/family", "meena"],
  ["me", "/app/me", "arjun"],
];

const widths = [360, 390, 412];

async function signIn(page, persona) {
  const response = await page.request.post(`${engine}/api/v1/auth/demo-login`, {
    data: { role: "personnel", persona_id: persona },
  });
  const login = await response.json();
  await page.goto(new URL("/login", base).toString(), { waitUntil: "domcontentloaded" });
  await page.evaluate((payload) => {
    sessionStorage.setItem("manobal.access_token", payload.access_token);
    sessionStorage.setItem("manobal.principal", JSON.stringify(payload.principal));
  }, login);
}

const browser = await chromium.launch();
for (const [slug, route, persona] of screens) {
  for (const width of widths) {
    const page = await browser.newPage({
      viewport: { width, height: 844 },
      deviceScaleFactor: 1,
    });
    await signIn(page, persona);
    await page.goto(new URL(route, base).toString(), {
      waitUntil: "domcontentloaded",
      timeout: 90_000,
    });
    await page.waitForLoadState("networkidle").catch(() => undefined);
    const loading = page.getByRole("status", { name: "Loading." });
    if ((await loading.count()) > 0) {
      await loading.first().waitFor({ state: "hidden", timeout: 45_000 }).catch(() => undefined);
    }
    await page.waitForTimeout(400);
    await page.screenshot({
      path: path.join(outDir, `p6-${slug}-${width}.png`),
      fullPage: true,
    });
    await page.close();
    console.log(`wrote p6-${slug}-${width}`);
  }
}
await browser.close();
