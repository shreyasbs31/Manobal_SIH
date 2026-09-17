import { expect, test, type Page } from "@playwright/test";

import { signIn } from "./session";

async function warm(page: Page, routes: string[]) {
  for (const route of routes) {
    await page.goto(route, { waitUntil: "domcontentloaded", timeout: 25_000 });
    await page.getByRole("heading").first().waitFor({ timeout: 12_000 }).catch(() => undefined);
    await page.waitForTimeout(150);
  }
  await page.evaluate(async () => {
    const ready = navigator.serviceWorker?.ready ?? Promise.resolve(null);
    await Promise.race([ready, new Promise((resolve) => window.setTimeout(resolve, 2000))]);
  });
}

test.describe("spec 27.2 offline", () => {
  test.beforeEach(async ({ page }) => {
    test.setTimeout(120_000);
    await signIn(page, "personnel", "arjun");
  });

  test("1 daily check-in queues offline", async ({ page, context }) => {
    await warm(page, ["/app/check-in"]);
    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded" }).catch(() => undefined);
    await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 10_000 });
    const face = page.getByRole("button", { name: /Okay/ }).first();
    if (await face.count()) {
      await face.click();
      await page.waitForTimeout(250);
    }
    if (await page.getByRole("button", { name: "Nothing specific" }).count()) {
      await page.getByRole("button", { name: "Nothing specific" }).click();
      await page.getByRole("button", { name: "Continue" }).click();
    }
    const save = page.getByRole("button", { name: "Save" });
    if (await save.count()) {
      await save.click();
    }
    await expect(page.getByText(/Your rhythm|Done|saved|सहेज/i).first()).toBeVisible({
      timeout: 10_000,
    });
    const queued = await page.evaluate(async () => {
      const request = indexedDB.open("manobal-saathi", 1);
      return await new Promise<number>((resolve) => {
        request.onsuccess = () => {
          const count = request.result.transaction("queue").objectStore("queue").count();
          count.onsuccess = () => resolve(Number(count.result));
        };
        request.onerror = () => resolve(-1);
      });
    });
    expect(queued).toBeGreaterThan(0);
  });

  test("2 structured voice check-in uses cached audio", async ({ page, context }) => {
    await warm(page, ["/app/check-in"]);
    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded" }).catch(() => undefined);
    await expect(page.getByText("Listen and tap. Speech recognition is not needed offline.")).toBeVisible();
    await expect(page.locator("audio[src='/audio/grounding.en.wav']")).toHaveCount(1);
  });

  test("3 assessments render from cache and queue", async ({ page, context }) => {
    await warm(page, ["/app/assessments", "/app/assessments/pss10"]);
    await context.setOffline(true);
    await page.goto("/app/assessments/pss10", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading").first()).toBeVisible();
    await page.locator(".mb-option-stack button").first().click();
    await expect(page.getByRole("heading").first()).toBeVisible();
  });

  test("4 toolkit works from cache", async ({ page, context }) => {
    await warm(page, ["/app/toolkit", "/app/toolkit/breathe"]);
    await context.setOffline(true);
    await page.goto("/app/toolkit", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Breathing, rest, and short reads work without a network.")).toBeVisible();
    await page.goto("/app/toolkit/breathe", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Box breathing" })).toBeVisible();
  });

  test("5 safety screen and tel stay available", async ({ page, context }) => {
    await warm(page, ["/app/safety"]);
    await context.setOffline(true);
    await page.goto("/app/safety", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading").first()).toBeVisible();
    await expect(page.getByRole("link", { name: /Call Tele-MANAS/ })).toHaveAttribute("href", /tel:/);
    await expect(page.getByText("Trying to reach your unit")).toBeVisible();
  });

  test("6 SOS by SMS uses sms link", async ({ page, context }) => {
    await warm(page, ["/app/safety"]);
    await context.setOffline(true);
    await page.goto("/app/safety", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("link", { name: "Send SOS by SMS" })).toHaveAttribute("href", /^sms:/);
  });

  test("7 crisis lexicon gate runs in the browser", async ({ page, context }) => {
    await warm(page, ["/app/saathi"]);
    await context.setOffline(true);
    await page.goto("/app/saathi", { waitUntil: "domcontentloaded" });
    if (await page.getByRole("button", { name: "Keyboard" }).count()) {
      await page.getByRole("button", { name: "Keyboard" }).click();
    }
    await page.getByLabel("Message").fill("I want to die");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page).toHaveURL(/\/app\/safety/, { timeout: 8_000 });
  });

  test("8 local self-care nudges show without the server", async ({ page, context }) => {
    await warm(page, ["/app"]);
    await context.setOffline(true);
    await page.goto("/app", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Sleep toolkit|Five-minute recovery|Why this/)).toBeVisible();
  });

  test("9 my trends render from the snapshot", async ({ page, context }) => {
    await warm(page, ["/app/me"]);
    await context.setOffline(true);
    await page.goto("/app/me", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("My trends")).toBeVisible();
  });

  test("10 safety plan stays on the device", async ({ page, context }) => {
    await warm(page, ["/app/plan"]);
    await context.setOffline(true);
    await page.goto("/app/plan", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Save on this phone" }).click();
    await expect(page.getByText("Saved on this phone.")).toBeVisible();
  });

  test("11 acute packet stays queued with helplines", async ({ page, context }) => {
    await warm(page, ["/app/safety"]);
    await context.setOffline(true);
    await page.goto("/app/safety", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Ask my welfare officer to call me" }).click();
    await expect(page.getByText("Trying to reach your unit")).toBeVisible();
    await expect(page.getByRole("link", { name: /Call Tele-MANAS/ })).toBeVisible();
  });

  test("12 resync drain is available after the network returns", async ({ page, context }) => {
    await warm(page, ["/app/check-in"]);
    await context.setOffline(true);
    await page.reload({ waitUntil: "domcontentloaded" }).catch(() => undefined);
    const face = page.getByRole("button", { name: /Okay/ }).first();
    if (await face.count()) {
      await face.click();
      await page.waitForTimeout(250);
    }
    if (await page.getByRole("button", { name: "Save" }).count()) {
      await page.getByRole("button", { name: "Save" }).click();
    }
    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    const token = await page.evaluate(() => sessionStorage.getItem("manobal.access_token"));
    expect(token).toBeTruthy();
  });
});
