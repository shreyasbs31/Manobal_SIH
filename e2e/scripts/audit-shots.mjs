import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const base = process.env.WEB_URL ?? "http://localhost:3000";
const engine = process.env.ENGINE_URL ?? "http://localhost:8000";
const outDir = path.resolve("artifacts/audit");
await mkdir(outDir, { recursive: true });

const shots = [
  ["landing", "/", "public", null],
  ["onboarding", "/stage?phone=/app/onboarding&console=/welfare&shot=onboarding", "personnel", "arjun"],
  ["checkin", "/stage?phone=/app/check-in&console=/welfare&shot=checkin", "personnel", "arjun"],
  ["voice", "/stage?phone=/app/saathi&console=/welfare&shot=voice", "personnel", "arjun"],
  ["drift", "/stage?phone=/app&console=/welfare&shot=drift", "personnel", "arjun"],
  ["workspace", "/stage?phone=/app/me&console=/welfare/cases/MB-4091&shot=workspace", "uwo", null],
  ["imran-thomas", "/stage?phone=/app&console=/lab&shot=imran-thomas", "wdec", null],
  ["formation", "/stage?phone=/app&console=/command&shot=formation", "commander", null],
  ["copilot", "/stage?phone=/app&console=/command&shot=copilot", "commander", null],
  ["roster", "/stage?phone=/app&console=/command/roster&shot=roster", "commander", null],
  ["deepak", "/stage?phone=/app/safety&console=/medical&shot=deepak", "mo", null],
  ["governance", "/stage?phone=/app&console=/governance&shot=governance", "wdec", null],
  ["lab", "/stage?phone=/app&console=/lab&shot=lab", "wdec", null],
  ["offline", "/stage?phone=/app/check-in&console=/architecture&shot=offline", "personnel", "arjun"],
  ["architecture", "/stage?phone=/app&console=/architecture&shot=architecture", "public", null],
  ["close", "/#ps-map", "public", null],
  ["karthik", "/stage?phone=/app/saathi&console=/welfare&shot=karthik", "personnel", "karthik"],
  ["rajesh", "/stage?phone=/app&console=/welfare&shot=rajesh", "personnel", "rajesh"],
  ["lalit", "/stage?phone=/app/talk&console=/welfare&shot=lalit", "personnel", "lalit"],
  ["meena", "/stage?phone=/app/rest&console=/command/roster&shot=meena", "personnel", "meena"],
];

async function reset(request) {
  const login = await request.post(`${engine}/api/v1/auth/demo-login`, {
    data: { role: "director" },
  });
  const body = await login.json();
  const result = await request.post(`${engine}/api/v1/demo/reset`, {
    headers: { authorization: `Bearer ${body.access_token}` },
  });
  const payload = await result.json();
  if (typeof payload.seconds === "number" && payload.seconds >= 20) {
    throw new Error(`reset took ${payload.seconds}s`);
  }
}

async function signIn(page, role, persona) {
  if (!role || role === "public") {
    return;
  }
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
const requestContext = await browser.newContext();
await reset(requestContext.request);

for (const [slug, route, role, persona] of shots) {
  await reset(requestContext.request);
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  await signIn(page, role, persona);
  await page.goto(new URL(route, base).toString(), {
    waitUntil: "domcontentloaded",
    timeout: 90_000,
  });
  await page.getByRole("heading", { level: 1 }).first().waitFor({ timeout: 20_000 }).catch(() => undefined);
  await page.waitForTimeout(1200);
  for (const frame of page.frames()) {
    const loading = frame.getByRole("status", { name: "Loading." });
    if ((await loading.count()) > 0) {
      await loading.first().waitFor({ state: "hidden", timeout: 25_000 }).catch(() => undefined);
    }
  }
  if (slug === "copilot") {
    const frame = page.frameLocator("iframe[title='Command console']");
    await frame.getByRole("button", { name: "Open copilot" }).click().catch(() => undefined);
    await frame.getByLabel("Question").fill("Charlie Coy mein kaun pareshan hai?").catch(() => undefined);
    await frame.getByRole("button", { name: "Ask" }).click().catch(() => undefined);
    await page.waitForTimeout(1500);
  }
  await page.waitForTimeout(1500);
  await page.screenshot({
    path: path.join(outDir, `${slug}-1920.png`),
    fullPage: false,
  });
  await page.close();
  console.log(`wrote ${slug}-1920.png`);
}

await requestContext.close();
await browser.close();
