import { chromium } from "@playwright/test";

async function runDryRunAll() {
  console.log("Starting dry run selector check for all pages and features...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  console.log("1. Stage page...");
  await page.goto("http://localhost:3000/stage?phone=/app/saathi&console=/welfare&shot=voice", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('iframe[name="mb-phone"]', { timeout: 15000 });
  await page.waitForSelector('iframe[name="mb-console"]', { timeout: 15000 });

  const phoneFrame = page.frame({ name: "mb-phone" });
  const consoleFrame = page.frame({ name: "mb-console" });

  if (!phoneFrame || !consoleFrame) throw new Error("Frames missing!");

  console.log("2. Checking Voice Native on Phone frame...");
  const playRecordedBtn = await phoneFrame.$("button:has-text('Play recorded check-in')");
  console.log("   Play recorded check-in button:", playRecordedBtn ? "FOUND" : "NOT FOUND");

  console.log("3. Checking Console nav rail items...");
  const hrefs = ["/command", "/command/roster", "/welfare", "/counsel", "/medical", "/hq", "/governance", "/dpo", "/lab"];
  for (const href of hrefs) {
    const link = await consoleFrame.$(`a[href='${href}']`);
    console.log(`   Nav link ${href}:`, link ? "FOUND" : "NOT FOUND");
  }

  await browser.close();
  console.log("Dry run check for all features COMPLETE!");
}

runDryRunAll().catch((err) => {
  console.error("Dry run failed:", err);
  process.exit(1);
});
