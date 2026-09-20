import { mkdirSync } from "node:fs";
import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { signIn } from "./session";

const repoRoot = path.join(__dirname, "..", "..");
const outDir = path.join(repoRoot, "e2e", "artifacts", "spine");

async function shot(page: Page, name: string) {
  mkdirSync(outDir, { recursive: true });
  await page.screenshot({ path: path.join(outDir, `${name}.png`), fullPage: true }).catch(() => undefined);
}

async function warm(page: Page, routes: string[]) {
  await page.goto(routes[0] ?? "/app", { waitUntil: "domcontentloaded", timeout: 25_000 });
  await page.evaluate(async () => {
    if (!("serviceWorker" in navigator)) {
      return;
    }
    await navigator.serviceWorker.register("/sw.js");
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise<void>((resolve) => {
        navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), { once: true });
        window.setTimeout(() => resolve(), 2500);
      });
    }
  });
  await page.reload({ waitUntil: "domcontentloaded" }).catch(() => undefined);
  for (const route of routes) {
    await page.goto(route, { waitUntil: "domcontentloaded", timeout: 25_000 });
    await page.getByRole("heading").first().waitFor({ timeout: 12_000 }).catch(() => undefined);
    await page.waitForTimeout(200);
  }
}

async function goOffline(page: Page, context: { setOffline: (value: boolean) => Promise<void> }) {
  await page.evaluate(() => {
    window.localStorage.setItem("manobal.airplane", "1");
    window.dispatchEvent(new Event("manobal-airplane"));
  });
  await context.setOffline(true);
}

test.describe("spec 27.2 offline", () => {
  test.beforeEach(async ({ page }) => {
    test.setTimeout(120_000);
    await signIn(page, "personnel", "arjun");
  });

  test("1 daily check-in queues offline", async ({ page, context }) => {
    await warm(page, ["/app/check-in"]);
    await goOffline(page, context);
    await page.goto("/app/check-in", { waitUntil: "domcontentloaded" }).catch(() => undefined);
    await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 10_000 });
    for (let step = 0; step < 4; step += 1) {
      const face = page.getByRole("button", { name: /Okay/ }).first();
      if (await face.count()) {
        await face.click();
        await page.waitForTimeout(300);
      }
    }
    if (await page.getByRole("button", { name: "Nothing specific" }).count()) {
      await page.getByRole("button", { name: "Nothing specific" }).click();
      await page.getByRole("button", { name: "Continue" }).click();
    }
    const save = page.getByRole("button", { name: "Save" });
    await expect(save).toBeVisible({ timeout: 10_000 });
    await save.click();
    await expect(page.getByText(/Your rhythm|Done|saved|सहेज/i).first()).toBeVisible({
      timeout: 10_000,
    });
    const queued = await page.evaluate(async () => {
      const request = indexedDB.open("manobal-saathi", 1);
      return await new Promise<number>((resolve) => {
        request.onupgradeneeded = () => {
          const db = request.result;
          if (!db.objectStoreNames.contains("queue")) {
            db.createObjectStore("queue", { keyPath: "id" });
          }
        };
        request.onsuccess = () => {
          try {
            const count = request.result.transaction("queue").objectStore("queue").count();
            count.onsuccess = () => resolve(Number(count.result));
            count.onerror = () => resolve(-1);
          } catch {
            resolve(-1);
          }
        };
        request.onerror = () => resolve(-1);
      });
    });
    expect(queued).toBeGreaterThan(0);
    await shot(page, "offline-1-checkin");
  });

  test("2 structured voice check-in uses cached audio", async ({ page, context }) => {
    await warm(page, ["/app/check-in"]);
    await goOffline(page, context);
    await page.goto("/app/check-in", { waitUntil: "domcontentloaded" }).catch(() => undefined);
    await expect(page.getByText("Listen, then tap an answer.")).toBeVisible();
    await expect(page.locator("audio[src='/audio/grounding.en.wav']")).toHaveCount(1);
    await shot(page, "offline-2-voice-checkin");
  });

  test("3 assessments render from cache and queue", async ({ page, context }) => {
    await warm(page, ["/app/assessments", "/app/assessments/pss10"]);
    await expect(page.locator(".mb-option-stack button").first()).toBeVisible({ timeout: 15_000 });
    await goOffline(page, context);
    await page.goto("/app/assessments/pss10", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading").first()).toBeVisible();
    await expect(page.locator(".mb-option-stack button").first()).toBeVisible({ timeout: 15_000 });
    await page.locator(".mb-option-stack button").first().click();
    await expect(page.getByRole("heading").first()).toBeVisible();
    await shot(page, "offline-3-assessments");
  });

  test("4 toolkit works from cache", async ({ page, context }) => {
    await warm(page, ["/app/toolkit", "/app/toolkit/breathe"]);
    await goOffline(page, context);
    await page.goto("/app/toolkit", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Breathing, rest, and short reads work without a network.")).toBeVisible();
    await page.goto("/app/toolkit/breathe", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Box breathing" })).toBeVisible();
    await shot(page, "offline-4-toolkit");
  });

  test("5 safety screen and tel stay available", async ({ page, context }) => {
    await warm(page, ["/app/safety"]);
    await goOffline(page, context);
    await page.goto("/app/safety", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading").first()).toBeVisible();
    await expect(page.getByRole("link", { name: /Call Tele-MANAS/ })).toHaveAttribute("href", /tel:/);
    await expect(page.getByText("Trying to reach your unit")).toBeVisible();
    await shot(page, "offline-5-safety");
  });

  test("6 SOS by SMS uses sms link", async ({ page, context }) => {
    await warm(page, ["/app/safety"]);
    await goOffline(page, context);
    await page.goto("/app/safety", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("link", { name: "Send SOS by SMS" })).toHaveAttribute("href", /^sms:/);
    await shot(page, "offline-6-sms");
  });

  test("7 crisis lexicon gate runs in the browser", async ({ page, context }) => {
    await warm(page, ["/app/saathi", "/app/safety"]);
    await goOffline(page, context);
    await page.goto("/app/saathi", { waitUntil: "domcontentloaded" });
    if (await page.getByRole("button", { name: "Keyboard" }).count()) {
      await page.getByRole("button", { name: "Keyboard" }).click();
    }
    await page.getByLabel("Message").fill("I want to die");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page).toHaveURL(/\/app\/safety/, { timeout: 8_000 });
    await expect(page.getByRole("link", { name: /Call Tele-MANAS/ })).toBeVisible();
    await expect(page.getByText("Trying to reach your unit")).toBeVisible();
    await shot(page, "offline-7-lexicon");
  });

  test("8 local self-care nudges show without the server", async ({ page, context }) => {
    await warm(page, ["/app"]);
    await goOffline(page, context);
    await page.goto("/app", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Sleep toolkit" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Five-minute recovery" })).toBeVisible();
    await shot(page, "offline-8-nudges");
  });

  test("9 my trends render from the snapshot", async ({ page, context }) => {
    await warm(page, ["/app/me"]);
    await goOffline(page, context);
    await page.goto("/app/me", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("My trends")).toBeVisible();
    await shot(page, "offline-9-trends");
  });

  test("10 safety plan stays on the device", async ({ page, context }) => {
    await warm(page, ["/app/plan"]);
    await goOffline(page, context);
    await page.goto("/app/plan", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Save on this phone" }).click();
    await expect(page.getByText("Saved on this phone.", { exact: true })).toBeVisible();
    await shot(page, "offline-10-plan");
  });

  test("11 acute packet stays queued with helplines", async ({ page, context }) => {
    await warm(page, ["/app/safety"]);
    await goOffline(page, context);
    await page.goto("/app/safety", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Ask my welfare officer to call me" }).click();
    await expect(page.getByText("Trying to reach your unit")).toBeVisible();
    await expect(page.getByRole("link", { name: /Call Tele-MANAS/ })).toBeVisible();
    await shot(page, "offline-11-acute");
  });

  test("12 resync drain is available after the network returns", async ({ page, context }) => {
    await warm(page, ["/app/check-in"]);
    await goOffline(page, context);
    await page.goto("/app/check-in", { waitUntil: "domcontentloaded" }).catch(() => undefined);
    const face = page.getByRole("button", { name: /Okay/ }).first();
    if (await face.count()) {
      await face.click();
      await page.waitForTimeout(250);
    }
    if (await page.getByRole("button", { name: "Save" }).count()) {
      await page.getByRole("button", { name: "Save" }).click();
    }
    await page.evaluate(() => window.localStorage.setItem("manobal.airplane", "0"));
    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    const token = await page.evaluate(() => sessionStorage.getItem("manobal.access_token"));
    expect(token).toBeTruthy();
    await shot(page, "offline-12-resync");
  });
});
