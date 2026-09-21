import { chromium } from "@playwright/test";
import fs from "fs";

const PHONE_ROUTES = [
  "/app",
  "/app/check-in",
  "/app/saathi",
  "/app/toolkit",
  "/app/toolkit/breathe",
  "/app/me",
  "/app/plan",
  "/app/safety",
  "/app/rest",
  "/app/family",
  "/app/concerns",
  "/app/assessments",
  "/app/buddy",
  "/app/talk",
];

const CONSOLE_ROUTES = [
  "/welfare",
  "/command",
  "/command/roster",
  "/medical",
  "/counsel",
  "/hq",
  "/governance",
  "/dpo",
  "/lab",
  "/admin",
  "/integrations",
  "/architecture",
];

async function dumpFrame(frame, label) {
  const info = await frame.evaluate(() => {
    const txt = (el) => (el.innerText || el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 70);
    const vis = (el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    };
    return {
      url: location.pathname + location.search,
      title: (document.querySelector("h1,h2")?.innerText || "").trim().slice(0, 90),
      headings: Array.from(document.querySelectorAll("h1,h2,h3")).filter(vis).map(txt).slice(0, 14),
      buttons: Array.from(document.querySelectorAll("button")).filter(vis).map(txt).filter(Boolean).slice(0, 40),
      links: Array.from(document.querySelectorAll("a[href]")).filter(vis)
        .map((a) => `${txt(a)} -> ${a.getAttribute("href")}`).slice(0, 30),
      inputs: Array.from(document.querySelectorAll("input,textarea,select")).filter(vis)
        .map((i) => `${i.tagName}[${i.type || ""}] name=${i.name || ""} ph=${i.placeholder || ""}`).slice(0, 15),
      scrollH: document.documentElement.scrollHeight,
    };
  });
  return { label, ...info };
}

async function main() {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  const results = [];

  await page.goto("http://localhost:3000/stage?phone=/app&console=/welfare", {
    waitUntil: "domcontentloaded",
  });
  await page.waitForSelector('iframe[name="mb-phone"]', { timeout: 20000 });
  await page.waitForSelector('iframe[name="mb-console"]', { timeout: 20000 });
  await page.waitForTimeout(6000); // let auth post + hydrate

  async function visit(frameName, route) {
    const handle = await page.$(`iframe[name="${frameName}"]`);
    await page.evaluate(
      ({ n, r }) => {
        document.querySelector(`iframe[name="${n}"]`).contentWindow.location.assign(r);
      },
      { n: frameName, r: route },
    );
    await page.waitForTimeout(3500);
    const frame = page.frame({ name: frameName });
    if (!frame) return { label: `${frameName}${route}`, error: "frame missing" };
    try {
      return await dumpFrame(frame, `${frameName} ${route}`);
    } catch (e) {
      return { label: `${frameName} ${route}`, error: e.message };
    }
  }

  for (const r of PHONE_ROUTES) {
    const d = await visit("mb-phone", r);
    results.push(d);
    console.log(`\n=== PHONE ${r} === (${d.url || "?"})`);
    console.log("  headings:", JSON.stringify(d.headings));
    console.log("  buttons :", JSON.stringify(d.buttons));
    console.log("  links   :", JSON.stringify(d.links));
    console.log("  inputs  :", JSON.stringify(d.inputs));
    console.log("  scrollH :", d.scrollH);
  }

  for (const r of CONSOLE_ROUTES) {
    const d = await visit("mb-console", r);
    results.push(d);
    console.log(`\n=== CONSOLE ${r} === (${d.url || "?"})`);
    console.log("  headings:", JSON.stringify(d.headings));
    console.log("  buttons :", JSON.stringify(d.buttons));
    console.log("  links   :", JSON.stringify(d.links));
    console.log("  inputs  :", JSON.stringify(d.inputs));
    console.log("  scrollH :", d.scrollH);
  }

  fs.writeFileSync("out/probe_screens.json", JSON.stringify(results, null, 2));
  console.log("\n[WROTE] out/probe_screens.json");
  await browser.close();
}

main().catch((e) => {
  console.error("PROBE FAILED", e);
  process.exit(1);
});
