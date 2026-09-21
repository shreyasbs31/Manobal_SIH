/**
 * Verify the two voice turns the demo depends on:
 *   1. a normal spoken check-in produces a visible Saathi reply
 *   2. a spoken acute phrase jumps straight to the safety screen
 */
import { chromium } from "@playwright/test";

const dump = async (page, tag) => {
  const f = page.frame({ name: "mb-phone" });
  const d = await f.evaluate(() => ({
    url: location.pathname + location.search,
    text: (document.querySelector("main")?.innerText || "").replace(/\s+\n/g, "\n").slice(0, 900),
    buttons: Array.from(document.querySelectorAll("button")).map((b) => b.innerText.trim()).filter(Boolean),
  }));
  console.log(`\n--- ${tag} (${d.url})`);
  console.log(d.text);
  console.log("buttons:", JSON.stringify(d.buttons));
  return d;
};

const navPhone = async (page, route, wait = 5000) => {
  await page.evaluate(
    (r) => document.querySelector('iframe[name="mb-phone"]').contentWindow.location.assign(r),
    route,
  );
  await page.waitForTimeout(wait);
};

async function main() {
  const browser = await chromium.launch({ args: ["--no-sandbox"] });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await ctx.newPage();
  page.on("console", (m) => {
    if (m.type() === "error") console.log("[console error]", m.text().slice(0, 200));
  });

  // Mount as the default persona (Arjun, who has no open acute case), then
  // navigate to the fixture. The fixture only supplies audio and a transcript,
  // so it does not have to match the signed-in persona - and mounting on
  // meena/deepak would start the phone on their seeded acute screen.
  await page.goto("http://localhost:3000/stage?phone=/app&console=/welfare",
    { waitUntil: "domcontentloaded" });
  await page.waitForSelector('iframe[name="mb-phone"]');
  await page.waitForTimeout(8000);
  await page.evaluate(() => localStorage.setItem("manobal.language", "en"));
  await navPhone(page, "/app/saathi?fixture=meena-en", 5000);

  await dump(page, "saathi mounted");

  // --- turn 1: an ordinary spoken check-in
  const f1 = page.frame({ name: "mb-phone" });
  const play = await f1.$("button:has-text('Play recorded check-in')");
  console.log("\n[play recorded button present]", !!play);
  if (play) {
    await play.click();
    for (const t of [4000, 4000, 4000, 4000]) {
      await page.waitForTimeout(t);
      const d = await page.frame({ name: "mb-phone" }).evaluate(
        () => (document.querySelector("main")?.innerText || "").slice(0, 500));
      console.log(`  +${t}ms:`, JSON.stringify(d.slice(0, 260)));
    }
  }
  await dump(page, "after normal voice turn");

  // --- turn 2: the acute phrase
  await navPhone(page, "/app/saathi?fixture=deepak-distress", 6000);
  const f2 = page.frame({ name: "mb-phone" });
  const play2 = await f2.$("button:has-text('Play recorded check-in')");
  console.log("\n[acute play button present]", !!play2);
  if (play2) {
    await play2.click();
    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(3000);
      const u = await page.frame({ name: "mb-phone" }).evaluate(() => location.pathname);
      console.log(`  +${(i + 1) * 3}s path:`, u);
      if (u.includes("safety")) break;
    }
  }
  await dump(page, "after acute voice turn");
  await browser.close();
}

main().catch((e) => { console.error(e); process.exit(1); });
