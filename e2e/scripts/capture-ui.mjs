import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const base = process.env.WEB_URL ?? "http://localhost:3000";
const tag = process.argv[2] ?? "after";
const outDir = path.resolve("artifacts/ui");
await mkdir(outDir, { recursive: true });

const pages = [
  ["landing", "/"],
  ["home", "/app"],
  ["check-in", "/app/check-in"],
  ["saathi", "/app/saathi"],
  ["safety", "/app/safety"],
  ["breathing", "/app/toolkit/breathe"],
  ["me", "/app/me"],
  ["toolkit", "/app/toolkit"],
  ["welfare", "/welfare"],
  ["case", "/welfare/cases/MB-4091"],
  ["command", "/command"],
  ["medical", "/medical"],
  ["governance", "/governance"],
  ["architecture", "/architecture"],
  ["stage", "/stage"],
  ["gallery", "/dev/components"],
];

const viewports = [
  { name: "390", width: 390, height: 844 },
  { name: "1440", width: 1440, height: 900 },
  { name: "1920", width: 1920, height: 1080 },
];

const fullPageSlugs = new Set(["landing", "me", "architecture"]);
const galleryThemes = [
  "Saathi dark",
  "Saathi high contrast",
  "Command dark",
  "Command light",
];

const browser = await chromium.launch();
for (const [slug, route] of pages) {
  for (const viewport of viewports) {
    if (slug !== "stage" && viewport.name === "1920") {
      continue;
    }
    if (slug === "stage" && viewport.name === "390") {
      continue;
    }
    const page = await browser.newPage({
      viewport,
      deviceScaleFactor: 1,
    });
    await page.goto(new URL(route, base).toString(), {
      waitUntil: "domcontentloaded",
      timeout: 90_000,
    });
    if (slug === "stage") {
      await page.locator("iframe").first().waitFor({ state: "attached", timeout: 30_000 });
      for (const frame of page.frames()) {
        if (frame === page.mainFrame()) {
          continue;
        }
        await frame.waitForLoadState("domcontentloaded").catch(() => undefined);
      }
      await page.waitForTimeout(5000);
    } else {
      await page.waitForTimeout(700);
    }
    await page.screenshot({
      path: path.join(outDir, `${tag}-${slug}-${viewport.name}.png`),
      fullPage: fullPageSlugs.has(slug) && viewport.name !== "1920",
    });
    if (slug === "gallery" && viewport.name === "1440") {
      for (const theme of galleryThemes) {
        await page.getByRole("button", { name: theme, exact: true }).click();
        await page.waitForTimeout(400);
        const file = theme.replaceAll(" ", "-").toLowerCase();
        await page.screenshot({
          path: path.join(outDir, `${tag}-gallery-${file}-1440.png`),
        });
        console.log(`wrote ${tag}-gallery-${file}-1440`);
      }
    }
    await page.close();
    console.log(`wrote ${tag}-${slug}-${viewport.name}`);
  }
}
await browser.close();
