import { chromium } from "@playwright/test";

async function runDryRun() {
  console.log("Starting dry run verification of selectors and timing...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  console.log("1. Testing landing page (http://localhost:3000/)...");
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
  const headline = await page.textContent("h1");
  console.log("   Headline found:", headline?.trim());

  page.on("console", (msg) => console.log("   [BROWSER LOG]", msg.type(), msg.text()));
  page.on("pageerror", (err) => console.error("   [BROWSER ERROR]", err));

  console.log("2. Testing Stage view (http://localhost:3000/stage?phone=/app/check-in&console=/welfare&shot=checkin)...");
  await page.goto("http://localhost:3000/stage?phone=/app/check-in&console=/welfare&shot=checkin", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(5000);
  console.log("   Page body content snippet:", (await page.content()).slice(0, 500));
  await page.waitForSelector('iframe[name="mb-phone"]', { timeout: 15000 });
  await page.waitForSelector('iframe[name="mb-console"]', { timeout: 15000 });

  const phoneFrame = page.frame({ name: "mb-phone" });
  const consoleFrame = page.frame({ name: "mb-console" });

  if (!phoneFrame) throw new Error("Phone frame missing!");
  if (!consoleFrame) throw new Error("Console frame missing!");

  console.log("   Phone frame loaded url:", phoneFrame.url());
  console.log("   Console frame loaded url:", consoleFrame.url());

  // Check check-in buttons in phone frame
  const faces = await phoneFrame.$$("button");
  console.log(`   Found ${faces.length} buttons in phone frame`);

  // Check welfare case card in console frame
  const caseCard = await consoleFrame.$("text=MB-4091");
  console.log("   MB-4091 case card in console frame:", caseCard ? "FOUND" : "NOT FOUND");

  // Check nav rail links in console frame
  const navLinks = await consoleFrame.$$("a, button");
  console.log(`   Found ${navLinks.length} interactive elements in console frame`);

  await browser.close();
  console.log("Dry run selector check COMPLETE!");
}

runDryRun().catch((err) => {
  console.error("Dry run failed:", err);
  process.exit(1);
});
