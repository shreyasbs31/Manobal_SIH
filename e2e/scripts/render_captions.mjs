/**
 * Render each caption cue to a transparent PNG.
 *
 * The local ffmpeg has no libass and no drawtext, so text cannot be drawn at
 * encode time. Chromium already renders this exact CSS in the demo, so we use it
 * as the type engine and composite the results with a plain overlay filter.
 *
 * Writes out/captions/cue_NNN.png and out/captions/manifest.json.
 */
import { chromium } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SRT = path.join(ROOT, "out", "manobal_demo_captions_en.srt");
const OUT = path.join(ROOT, "out", "captions");

function loadCues() {
  const toSeconds = (stamp) => {
    const [h, m, rest] = stamp.split(":");
    const [sec, ms] = rest.split(",");
    return +h * 3600 + +m * 60 + +sec + +ms / 1000;
  };
  return fs.readFileSync(SRT, "utf8").trim().split(/\n\s*\n/).map((block) => {
    const lines = block.split("\n");
    const [from, to] = lines[1].split(" --> ");
    return { start: toSeconds(from), end: toSeconds(to), text: lines.slice(2).join("\n") };
  });
}

const PAGE = `<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;padding:0;background:transparent}
  #cap{display:inline-block;max-width:1120px;padding:11px 22px;border-radius:9px;
    background:rgba(8,10,12,.84);color:#fff;
    font-family:Helvetica,Arial,system-ui,sans-serif;font-size:25px;line-height:1.36;
    font-weight:500;text-align:center;letter-spacing:.1px;white-space:pre-line;
    box-shadow:0 2px 18px rgba(0,0,0,.35)}
</style></head><body><div id="cap"></div></body></html>`;

async function main() {
  const cues = loadCues();
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch({ args: ["--no-sandbox"] });
  const page = await browser.newPage({
    viewport: { width: 1400, height: 300 },
    deviceScaleFactor: 1,
  });
  await page.setContent(PAGE);

  const manifest = [];
  for (const [i, cue] of cues.entries()) {
    await page.evaluate((t) => {
      document.getElementById("cap").textContent = t;
    }, cue.text);
    const el = await page.$("#cap");
    const file = `cue_${String(i + 1).padStart(3, "0")}.png`;
    await el.screenshot({ path: path.join(OUT, file), omitBackground: true });
    const box = await el.boundingBox();
    manifest.push({
      file,
      start: +cue.start.toFixed(3),
      end: +cue.end.toFixed(3),
      w: Math.round(box.width),
      h: Math.round(box.height),
      text: cue.text,
    });
  }
  fs.writeFileSync(path.join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log(`rendered ${manifest.length} caption images -> ${OUT}`);
  const widest = manifest.reduce((a, b) => (b.w > a.w ? b : a));
  console.log(`widest ${widest.w}x${widest.h}px  "${widest.text.replace(/\n/g, " / ")}"`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
