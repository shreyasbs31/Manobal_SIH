import { chromium } from "@playwright/test";
const b = await chromium.launch({ args:["--no-sandbox"] });
const page = await (await b.newContext({viewport:{width:1920,height:1080}})).newPage();
await page.goto("http://localhost:3000/stage?phone=/app&console=/command/roster",{waitUntil:"domcontentloaded"});
await page.waitForSelector('iframe[name="mb-console"]'); await page.waitForTimeout(8000);
const f = page.frame({name:"mb-console"});
console.log(await f.evaluate(() => {
  const out = [];
  const svg = document.querySelector(".mb-screen-nav-btn svg");
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch { continue; }
    const walk = (list) => { for (const r of list) {
      if (r.cssRules) { walk(r.cssRules); continue; }
      if (!r.selectorText) continue;
      let matches = false;
      try { matches = svg.matches(r.selectorText); } catch { continue; }
      if (matches && /width|flex|display|size/i.test(r.style.cssText)) {
        out.push(`${r.selectorText}  =>  ${r.style.cssText.slice(0,160)}`);
      }
    }};
    walk(rules);
  }
  // also what matches the parent button
  const btn = document.querySelector(".mb-screen-nav-btn");
  const parentRules = [];
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch { continue; }
    const walk = (list) => { for (const r of list) {
      if (r.cssRules) { walk(r.cssRules); continue; }
      if (!r.selectorText) continue;
      let m=false; try { m = btn.matches(r.selectorText); } catch { continue; }
      if (m && /width|padding|display/i.test(r.style.cssText)) parentRules.push(`${r.selectorText} => ${r.style.cssText.slice(0,160)}`);
    }};
    walk(rules);
  }
  return "SVG RULES:\n" + out.join("\n") + "\n\nBUTTON RULES:\n" + parentRules.join("\n");
}));
await b.close();
