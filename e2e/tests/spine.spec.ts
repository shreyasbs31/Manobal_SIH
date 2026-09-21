import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page, type Request } from "@playwright/test";

import { signIn } from "./session";

const engine = process.env.ENGINE_URL ?? "http://localhost:8000";
const repoRoot = path.join(__dirname, "..", "..");
const outDir = path.join(repoRoot, "e2e", "artifacts", "spine");

async function directorToken(request: Page["request"]): Promise<string> {
  const login = await request.post(`${engine}/api/v1/auth/demo-login`, {
    data: { role: "director" },
  });
  const body = (await login.json()) as { access_token: string };
  return body.access_token;
}

async function resetDemo(request: Page["request"]): Promise<void> {
  const token = await directorToken(request);
  const result = await request.post(`${engine}/api/v1/demo/reset`, {
    headers: { authorization: `Bearer ${token}` },
  });
  const payload = (await result.json()) as { seconds?: number };
  expect(payload.seconds ?? 99).toBeLessThan(20);
}

function engineLogs(since = "10m"): string {
  const root = path.join(__dirname, "..", "..");
  try {
    return execSync(
      `docker compose --env-file infra/.env -f infra/docker-compose.yml logs engine --since ${since}`,
      { encoding: "utf8", cwd: root },
    ).replace(/access_token=[^&\s"]+/g, "access_token=redacted");
  } catch {
    try {
      return execSync("docker logs manobal-engine-1 --since 10m", { encoding: "utf8", cwd: root });
    } catch {
      return "";
    }
  }
}

async function capture(page: Page, name: string, network: Request[]): Promise<void> {
  mkdirSync(outDir, { recursive: true });
  await page.screenshot({ path: path.join(outDir, `${name}.png`), fullPage: true }).catch(() => undefined);
  const urls = network.map((item) => `${item.method()} ${item.url()}`);
  writeFileSync(path.join(outDir, `${name}.network.log`), urls.join("\n"));
  writeFileSync(path.join(outDir, `${name}.engine.log`), engineLogs());
}

test.describe.configure({ mode: "serial" });

test.describe("demo spine", () => {
  test.setTimeout(180_000);

  test("arjun hindi voice turn", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await resetDemo(page.request);
    await signIn(page, "personnel", "arjun");
    await page.goto("/app/saathi?fixture=arjun-hi");
    await page.getByRole("button", { name: "Play recorded check-in" }).first().click();
    await expect(page.locator('.mb-caption-line[data-speaker="saathi"]').first()).toBeVisible({
      timeout: 60_000,
    });
    await capture(page, "arjun-hindi-voice", network);
  });

  test("karthik tamil voice turn", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "personnel", "karthik");
    await page.goto("/app/saathi?fixture=karthik-ta");
    await page.getByRole("button", { name: "Play recorded check-in" }).first().click();
    await expect(page.getByText(/ooyvu|தூக்கம்|rest|ungalai/i).first()).toBeVisible({ timeout: 60_000 });
    await capture(page, "karthik-tamil-voice", network);
  });

  test("deepak typed distress", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "personnel", "deepak");
    await page.goto("/app/saathi");
    await page.getByRole("button", { name: "Keyboard" }).click();
    await page.getByLabel("Message").fill("main jeena nahi chahta");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page).toHaveURL(/\/app\/safety/, { timeout: 15_000 });
    await expect(page.getByRole("heading").first()).toBeVisible();
    await capture(page, "deepak-typed-distress", network);
  });

  test("deepak spoken distress and T4 under 5s", async ({ page, context, request }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "personnel", "deepak");
    await page.goto("/app/saathi?fixture=deepak-distress");
    const uwoLogin = await request.post(`${engine}/api/v1/auth/demo-login`, {
      data: { role: "uwo" },
    });
    const moLogin = await request.post(`${engine}/api/v1/auth/demo-login`, {
      data: { role: "mo" },
    });
    const uwoToken = ((await uwoLogin.json()) as { access_token: string }).access_token;
    const moToken = ((await moLogin.json()) as { access_token: string }).access_token;
    const started = Date.now();
    await page.getByRole("button", { name: "Play recorded check-in" }).first().click();
    const t4Seen = (async () => {
      while (Date.now() - started < 5_000) {
        const welfare = await request.get(`${engine}/api/v1/welfare/queue`, {
          headers: { authorization: `Bearer ${uwoToken}` },
        });
        const medical = await request.get(`${engine}/api/v1/medical/acute`, {
          headers: { authorization: `Bearer ${moToken}` },
        });
        const welfareText = await welfare.text();
        const medicalText = await medical.text();
        if (/T4|MB-6604/.test(welfareText) && /T4|MB-6604/.test(medicalText)) {
          return { welfareText, medicalText, ms: Date.now() - started };
        }
        await page.waitForTimeout(150);
      }
      return null;
    })();
    await expect(page).toHaveURL(/\/app\/safety/, { timeout: 20_000 });
    const found = await t4Seen;
    if (!found) {
      throw new Error("T4 missing on welfare or medical within 5s");
    }
    expect(found.ms).toBeLessThan(5_000);
    const welfarePage = await context.newPage();
    await signIn(welfarePage, "uwo");
    await welfarePage.goto("/welfare");
    await expect(welfarePage.getByText(/T4|MB-6604|acute/i).first()).toBeVisible({ timeout: 10_000 });
    const medicalPage = await context.newPage();
    await signIn(medicalPage, "mo");
    await medicalPage.goto("/medical");
    await expect(medicalPage.getByText(/T4|MB-6604/i).first()).toBeVisible({ timeout: 10_000 });
    await capture(page, "deepak-spoken-distress", network);
    await welfarePage.screenshot({ path: path.join(outDir, "deepak-t4-welfare.png") });
    await medicalPage.screenshot({ path: path.join(outDir, "deepak-t4-medical.png") });
  });

  test("hindi case brief with field references", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "uwo");
    await page.goto("/welfare/cases/MB-4091");
    await page.getByRole("button", { name: "Hindi" }).click();
    await expect(page.locator(".mb-brief-ref").first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTitle(/T3|workload|REST|onset|tier/i).or(page.locator(".mb-brief-ref")).first()).toBeVisible();
    await capture(page, "hindi-case-brief", network);
  });

  test("copilot aggregate hindi live with chart", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "commander");
    await page.goto("/command");
    await page.getByRole("button", { name: "Hindi" }).click();
    await page.getByRole("button", { name: "सहायक से पूछें" }).click();
    await page.getByRole("button", { name: "रात की पाली" }).click();
    await page.getByRole("button", { name: "पूछें" }).click();
    await expect(page.locator(".mb-copilot p").first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Answer source main/i)).toBeVisible();
    await expect(page.getByText(/naam nahi|kaun pareshan/i)).toHaveCount(0);
    await expect(page.getByTestId("copilot-chart")).toBeVisible();
    await capture(page, "copilot-aggregate-hi", network);
  });

  test("copilot individual refused", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "commander");
    await page.goto("/command");
    await page.getByRole("button", { name: "Ask copilot" }).click();
    await page.getByLabel("Question").fill("Charlie Coy mein kaun pareshan hai?");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByText(/Main kisi jawan ka naam nahi de sakta/)).toBeVisible({ timeout: 15_000 });
    await capture(page, "copilot-individual-refuse", network);
  });

  test("deepgram outage fallback", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    const token = await directorToken(page.request);
    await page.request.post(`${engine}/api/v1/demo/outage`, {
      headers: { authorization: `Bearer ${token}` },
      data: { provider: "deepgram", opened: true },
    });
    await signIn(page, "personnel", "meena");
    await page.goto("/app/saathi?fixture=meena-en");
    await page.getByRole("button", { name: "Play recorded check-in" }).first().click();
    await expect(page.getByText(/rest|sleep|duty|aaram/i).first()).toBeVisible({ timeout: 60_000 });
    await capture(page, "deepgram-outage", network);
    await page.request.post(`${engine}/api/v1/demo/outage`, {
      headers: { authorization: `Bearer ${token}` },
      data: { provider: "deepgram", opened: false },
    });
  });

  test("lab numbers from computed source", async ({ page }) => {
    const network: Request[] = [];
    page.on("request", (item) => network.push(item));
    await signIn(page, "wdec");
    await page.goto("/lab");
    await expect(page.getByText(/Source:/)).toBeVisible();
    await expect(page.getByText(/Imran stays T1/)).toBeVisible();
    await expect(page.getByText(/Thomas stays T0/)).toBeVisible();
    await capture(page, "lab-numbers", network);
    await page.goto("/governance");
    await expect(page.getByText(/Source:/)).toBeVisible();
    await capture(page, "governance-numbers", network);
  });
});
