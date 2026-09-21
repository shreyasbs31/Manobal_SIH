import { chromium } from "@playwright/test";
const b = await chromium.launch({ args:["--no-sandbox"] });
const page = await (await b.newContext({viewport:{width:1920,height:1080}})).newPage();
await page.goto("http://localhost:3000/stage?phone=/app&console=/command/roster",{waitUntil:"domcontentloaded"});
await page.waitForSelector('iframe[name="mb-console"]'); await page.waitForTimeout(8000);
const f = page.frame({name:"mb-console"});
console.log(JSON.stringify(await f.evaluate(() => {
  const pick = (svg) => { const c = getComputedStyle(svg); return {
    width:c.width, height:c.height, minWidth:c.minWidth, flex:c.flex, flexBasis:c.flexBasis,
    flexShrink:c.flexShrink, display:c.display, aspectRatio:c.aspectRatio, boxSizing:c.boxSizing,
    attrW: svg.getAttribute("width"), rect: svg.getBoundingClientRect().width }; };
  const navSvg = document.querySelector(".mb-screen-nav-btn svg");
  const okSvg = document.querySelector(".mb-topbar-end .mb-ghost svg");
  return { broken: navSvg?pick(navSvg):null, workingTopbar: okSvg?pick(okSvg):null };
}), null, 1));
await b.close();
