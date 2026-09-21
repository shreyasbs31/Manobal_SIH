/**
 * Screenshot every console page at the size it appears inside the demo stage,
 * so layout problems can be judged against what the video actually shows.
 * Writes out/ui_audit/<name>.png
 */
import { chromium } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const OUT = path.join(ROOT, "out", "ui_audit");

const ROUTES = [
  ["welfare", "/welfare"],
  ["case", "/welfare/cases/MB-4091"],
  ["command", "/command"],
  ["roster", "/command/roster"],
  ["medical", "/medical"],
  ["counsel", "/counsel"],
  ["hq", "/hq"],
  ["governance", "/governance"],
  ["dpo", "/dpo"],
  ["integrations", "/integrations"],
  ["lab", "/lab"],
  ["admin", "/admin"],
];

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await ctx.newPage();

  await page.goto("http://localhost:3000/stage?phone=/app&console=/welfare", {
    waitUntil: "domcontentloaded",
  });
  await page.waitForSelector('iframe[name="mb-console"]');
  await page.waitForTimeout(7000);

  const report = [];
  for (const [name, route] of ROUTES) {
    await page.evaluate(
      (r) => document.querySelector('iframe[name="mb-console"]').contentWindow.location.assign(r),
      route,
    );
    await page.waitForTimeout(6500);
    const frame = page.frame({ name: "mb-console" });
    const el = await page.$('iframe[name="mb-console"]');
    await el.screenshot({ path: path.join(OUT, `${name}.png`) });

    // Measure things that usually signal a cramped or broken layout.
    const m = await frame.evaluate(() => {
      const main = document.querySelector("main");
      const vis = (e) => {
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      };
      const all = Array.from(main ? main.querySelectorAll("*") : []).filter(vis);
      const overflowX = all.filter((e) => e.scrollWidth > e.clientWidth + 2).length;
      const overflowY = all.filter((e) => e.scrollHeight > e.clientHeight + 2).length;
      const r = main?.getBoundingClientRect();
      return {
        innerW: window.innerWidth,
        innerH: window.innerHeight,
        mainH: r ? Math.round(r.height) : 0,
        docH: document.documentElement.scrollHeight,
        clippedX: overflowX,
        clippedY: overflowY,
        cut: main ? Math.max(0, Math.round(main.scrollHeight - main.clientHeight)) : 0,
      };
    });
    report.push({ name, route, ...m });
    console.log(
      `${name.padEnd(13)} main ${String(m.mainH).padStart(4)}px  doc ${String(m.docH).padStart(4)}px ` +
      `viewport ${m.innerW}x${m.innerH}  clipped-x ${m.clippedX}  clipped-y ${m.clippedY}  main-cut ${m.cut}px`,
    );
  }
  fs.writeFileSync(path.join(OUT, "report.json"), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(`\nshots -> ${OUT}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
