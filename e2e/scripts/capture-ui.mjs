import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const base = process.env.WEB_URL ?? "http://localhost:3001";
const tag = process.argv[2] ?? "before";
const outDir = path.resolve("artifacts/ui");
await mkdir(outDir, { recursive: true });

const pages = [
  ["landing", "/"],
  ["home", "/app"],
  ["saathi", "/app/saathi"],
  ["toolkit", "/app/toolkit"],
  ["me", "/app/me"],
  ["welfare", "/welfare"],
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
];

const browser = await chromium.launch();
for (const [slug, route] of pages) {
  for (const viewport of viewports) {
    const page = await browser.newPage({
      viewport,
      deviceScaleFactor: 1,
    });
    await page.goto(new URL(route, base).toString(), {
      waitUntil: "domcontentloaded",
      timeout: 90_000,
    });
    await page.waitForTimeout(400);
    await page.screenshot({
      path: path.join(outDir, `${tag}-${slug}-${viewport.name}.png`),
      fullPage: viewport.name === "390",
    });
    await page.close();
    console.log(`wrote ${tag}-${slug}-${viewport.name}`);
  }
}
await browser.close();
