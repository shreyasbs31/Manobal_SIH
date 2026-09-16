import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const base = process.env.WEB_URL ?? "http://localhost:3000";
const engine = process.env.ENGINE_URL ?? "http://localhost:8000";
const outDir = path.resolve("artifacts/ui");
await mkdir(outDir, { recursive: true });

const screens = [
  ["welfare", "/welfare", "uwo", null],
  ["case", "/welfare/cases/MB-4091", "uwo", null],
  ["counsel", "/counsel", "counsellor", null],
  ["medical", "/medical", "mo", null],
  ["command", "/command", "commander", null],
  ["roster", "/command/roster", "commander", null],
  ["hq", "/hq", "hq", null],
];

const widths = [1280, 1440, 1920];
const themes = ["dark", "light"];

async function signIn(page, role, persona) {
  const response = await page.request.post(`${engine}/api/v1/auth/demo-login`, {
    data: { role, persona_id: persona },
  });
  const login = await response.json();
  await page.goto(new URL("/login", base).toString(), { waitUntil: "domcontentloaded" });
  await page.evaluate((payload) => {
    sessionStorage.setItem("manobal.access_token", payload.access_token);
    sessionStorage.setItem("manobal.principal", JSON.stringify(payload.principal));
  }, login);
}

const browser = await chromium.launch();
for (const [slug, route, role, persona] of screens) {
  for (const width of widths) {
    for (const theme of themes) {
      const page = await browser.newPage({
        viewport: { width, height: 900 },
        deviceScaleFactor: 1,
      });
      await signIn(page, role, persona);
      await page.goto(new URL(route, base).toString(), {
        waitUntil: "domcontentloaded",
        timeout: 90_000,
      });
      await page.waitForLoadState("networkidle").catch(() => undefined);
      await page.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 45_000 }).catch(() => undefined);
      await page.locator("select[aria-label='Theme']").selectOption(theme).catch(() => undefined);
      const loading = page.getByRole("status", { name: "Loading." });
      if ((await loading.count()) > 0) {
        await loading.first().waitFor({ state: "hidden", timeout: 45_000 }).catch(() => undefined);
      }
      await page.waitForTimeout(400);
      await page.screenshot({
        path: path.join(outDir, `p7-${slug}-${theme}-${width}.png`),
        fullPage: true,
      });
      await page.close();
      console.log(`wrote p7-${slug}-${theme}-${width}`);
    }
  }
}
await browser.close();
