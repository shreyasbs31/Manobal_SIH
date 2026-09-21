import { chromium } from "@playwright/test";
const b = await chromium.launch({ args:["--no-sandbox"] });
const ctx = await b.newContext({ viewport:{width:1920,height:1080} });
const page = await ctx.newPage();
await page.goto("http://localhost:3000/stage?phone=/app&console=/command/roster",{waitUntil:"domcontentloaded"});
await page.waitForSelector('iframe[name="mb-console"]'); await page.waitForTimeout(8000);
const f = page.frame({name:"mb-console"});
console.log(JSON.stringify(await f.evaluate(() => {
  const nav = document.querySelector(".mb-screen-nav");
  if (!nav) return {nav:null};
  const out = { html: nav.outerHTML.slice(0,600), buttons: [] };
  for (const btn of nav.querySelectorAll("button")) {
    const svg = btn.querySelector("svg");
    const cs = svg ? getComputedStyle(svg) : null;
    const br = btn.getBoundingClientRect();
    out.buttons.push({
      label: btn.getAttribute("aria-label"),
      btnBox: [Math.round(br.width), Math.round(br.height)],
      hasSvg: !!svg,
      svgBox: svg ? [Math.round(svg.getBoundingClientRect().width), Math.round(svg.getBoundingClientRect().height)] : null,
      stroke: cs?.stroke, color: cs?.color, opacity: cs?.opacity, display: cs?.display, visibility: cs?.visibility,
      svgHtml: svg ? svg.outerHTML.slice(0,200) : null,
    });
  }
  return out;
}), null, 1));
await b.close();
