/**
 * MANOBAL demo recorder - single 240s take driven by demo/timeline.json.
 *
 *   node e2e/scripts/record_demo.mjs --dry    fast rehearsal, asserts every step
 *   node e2e/scripts/record_demo.mjs          real-time take with video capture
 *
 * Design notes earned the hard way:
 *  - Frame handles are re-resolved on every action. Never cache them.
 *  - Every interaction asserts. A missing selector fails loudly instead of
 *    silently no-opping, which is how the previous take froze the phone.
 *  - Console pages do not scroll (scrollHeight == innerHeight); motion there
 *    comes from clicks. Phone pages do scroll.
 *  - Routes are pre-warmed, because a cold Next.js route takes ~10s to compile.
 */
import { chromium } from "@playwright/test";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const TIMELINE = JSON.parse(fs.readFileSync(path.join(ROOT, "demo", "timeline.json"), "utf8"));
const DRY = process.argv.includes("--dry");
const BASE = "http://localhost:3000";

const MARK = {};
for (const s of TIMELINE.segments) MARK[s.id] = s.start;
const seg = (id, offset = 0) => MARK[id] + offset;

/** Read the caption sidecar so on-screen text and the .srt can never diverge. */
function loadCues() {
  const file = path.join(ROOT, "out", "manobal_demo_captions_en.srt");
  if (!fs.existsSync(file)) {
    throw new Error(`captions not built yet: ${file} (run scripts/build_captions.py)`);
  }
  const toSeconds = (stamp) => {
    const [h, m, rest] = stamp.split(":");
    const [sec, ms] = rest.split(",");
    return +h * 3600 + +m * 60 + +sec + +ms / 1000;
  };
  return fs.readFileSync(file, "utf8").trim().split(/\n\s*\n/).map((block) => {
    const lines = block.split("\n");
    const [from, to] = lines[1].split(" --> ");
    return { start: toSeconds(from), end: toSeconds(to), text: lines.slice(2).join("\n") };
  });
}

const failures = [];
const slowSteps = [];
const lateLoads = [];
let CUES = [];
const log = [];

/* ---------------------------------------------------------------- helpers */

const frameOf = (page, name) => {
  const f = page.frame({ name });
  if (!f) throw new Error(`iframe "${name}" not present`);
  return f;
};

/** The iframe element mounts before its frame is attached and named. */
async function waitForFrame(page, name, timeout = 20000) {
  const deadline = Date.now() + timeout;
  await page.waitForSelector(`iframe[name="${name}"]`, { timeout });
  while (Date.now() < deadline) {
    if (page.frame({ name })) return page.frame({ name });
    await page.waitForTimeout(120);
  }
  throw new Error(`frame "${name}" never attached within ${timeout}ms`);
}

/** Resolve a selector, waiting briefly for it to render. Throws if it never does. */
async function must(page, frameName, selector, what, timeout = DRY ? 6000 : 3500) {
  const frame = frameOf(page, frameName);
  try {
    return await frame.waitForSelector(selector, { state: "visible", timeout });
  } catch {
    throw new Error(`${what}: no visible element for ${selector} on ${frame.url()}`);
  }
}

async function click(page, frameName, selector, what) {
  const el = await must(page, frameName, selector, what);
  await el.click({ timeout: DRY ? 6000 : 3500 });
}

/** Reject rather than hang, so a busy renderer cannot stall the timeline. */
function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`${label} exceeded ${ms}ms`)), ms)),
  ]);
}

/** Navigate an iframe in place. sessionStorage (and its auth) survives. */
async function nav(page, frameName, route, { settle = 900 } = {}) {
  try {
    await withTimeout(
      page.evaluate(
        ({ n, r }) => {
          const f = document.querySelector(`iframe[name="${n}"]`);
          if (!f) throw new Error(`iframe ${n} missing`);
          f.contentWindow.location.assign(r);
        },
        { n: frameName, r: route },
      ),
      DRY ? 15000 : 4000,
      `nav(${frameName} -> ${route})`,
    );
  } catch (e) {
    // The assign may well have been issued before the page went busy; record it
    // and carry on rather than letting one screen swallow later marks.
    if (DRY) throw e;
    lateLoads.push(`nav(${frameName} -> ${route}): ${e.message}`);
  }
  await page.waitForTimeout(settle);
}

/**
 * Wait until a frame has really rendered, by waiting for a selector that only
 * exists once the screen is up. A text-length heuristic was tried first and was
 * badly wrong: short screens like the check-in never reached the threshold, so
 * the wait burned its whole timeout and swallowed the segment that followed.
 * Throws on timeout so a slow screen is a loud failure, not silent drift.
 */
async function waitLoaded(page, frameName, selector, { timeout = 12000 } = {}) {
  const started = Date.now();
  const frame = frameOf(page, frameName);
  // In a real take the navigation has already been issued and the page will
  // render whether or not we sit here waiting, so blocking past our budget only
  // pushes every later mark late. Rehearsal still waits the full timeout and
  // throws, so a genuinely broken selector is caught before we record.
  const budget = DRY ? timeout : Math.min(timeout, 5200);
  try {
    await frame.waitForSelector(selector, { state: "visible", timeout: budget });
  } catch {
    const msg = `waitLoaded(${frameName}): "${selector}" not visible within ` +
      `${budget}ms on ${frame.url()}`;
    if (DRY) throw new Error(msg);
    lateLoads.push(msg);
  }
  await page.waitForTimeout(150);
  return Date.now() - started;
}

async function scrollFrame(page, frameName, top, smooth = true) {
  const frame = frameOf(page, frameName);
  await frame.evaluate(
    ({ t, s }) => window.scrollTo({ top: t, behavior: s ? "smooth" : "auto" }),
    { t: top, s: smooth },
  );
}

async function setPhoneLang(page, lang) {
  const frame = frameOf(page, "mb-phone");
  await frame.evaluate((l) => {
    window.localStorage.setItem("manobal.language", l);
    window.dispatchEvent(new Event("manobal-language"));
  }, lang);
}

/* Check-in is a small state machine; drive whatever step is actually on screen
   so a "busy day" variant (fewer questions) cannot desync the take. */
async function advanceCheckIn(page, { score = 4, tags = ["Duty", "Family"] } = {}) {
  const frame = frameOf(page, "mb-phone");
  const faces = await frame.$$(".mb-emoji-row button");
  if (faces.length) {
    await faces[Math.min(score, faces.length) - 1].click();
    return "face";
  }
  const tagButtons = await frame.$$(".mb-tag-row button");
  if (tagButtons.length) {
    for (const label of tags) {
      const el = await frame.$(`.mb-tag-row button:has-text("${label}")`);
      if (el) await el.click();
      await page.waitForTimeout(140);
    }
    const cont = await frame.$("button.mb-primary");
    if (!cont) throw new Error("check-in: tag step has no primary button");
    await cont.click();
    return "tags";
  }
  const primary = await frame.$("button.mb-primary");
  if (primary) {
    await primary.click();
    return "save";
  }
  const done = await frame.$("a.mb-primary");
  if (done) return "done";
  throw new Error(`check-in: no recognisable step on ${frame.url()}`);
}

/* ------------------------------------------------------------- the overlay */

/**
 * Draw the persistent label and the captions into the page itself.
 *
 * The local ffmpeg has no libass and no drawtext, so captions cannot be burned
 * in afterwards. Rendering them here is better anyway: the page runs its own
 * clock seeded from the take's t0, so every cue is frame-accurate against the
 * narration it was measured from, and styling is plain CSS.
 *
 * Re-injected after each top-level navigation, carrying the elapsed offset so
 * the caption clock stays continuous across the page change.
 */
async function injectOverlay(page, cues, elapsedSeconds) {
  await page.evaluate(
    ({ cueList, elapsed }) => {
      document.getElementById("mb-demo-overlay")?.remove();
      if (window.__mbCaptionTimer) clearInterval(window.__mbCaptionTimer);

      const el = document.createElement("div");
      el.id = "mb-demo-overlay";
      el.style.cssText =
        "position:fixed;inset:0;pointer-events:none;z-index:2147483647;" +
        "font-family:Helvetica,Arial,system-ui,sans-serif";
      el.innerHTML = `
        <div style="position:absolute;bottom:16px;left:22px;font-size:13px;font-weight:600;
          letter-spacing:.5px;color:rgba(255,255,255,.74);background:rgba(0,0,0,.62);
          padding:5px 11px;border-radius:4px">PROTOTYPE · SYNTHETIC DATA</div>
        <div id="mb-caption-wrap" style="position:absolute;bottom:52px;left:0;right:0;
          display:flex;justify-content:center">
          <div id="mb-caption" style="max-width:1120px;padding:11px 22px;border-radius:9px;
            background:rgba(8,10,12,.82);color:#fff;font-size:25px;line-height:1.36;
            font-weight:500;text-align:center;letter-spacing:.1px;
            box-shadow:0 2px 18px rgba(0,0,0,.35);opacity:0;
            transition:opacity 120ms linear;white-space:pre-line"></div>
        </div>`;
      document.body.appendChild(el);

      const box = el.querySelector("#mb-caption");
      const start = performance.now() - elapsed * 1000;
      const tick = () => {
        const t = (performance.now() - start) / 1000;
        const cue = cueList.find((c) => t >= c.start && t < c.end);
        if (cue) {
          if (box.textContent !== cue.text) box.textContent = cue.text;
          box.style.opacity = "1";
        } else {
          box.style.opacity = "0";
        }
      };
      tick();
      window.__mbCaptionTimer = setInterval(tick, 60);
    },
    { cueList: cues, elapsed: elapsedSeconds },
  );
}

/* ------------------------------------------------------------------ script */
/* Each entry: [mark seconds, description, action]. Kept flat and declarative
   so the dry run and the real take execute exactly the same sequence. */

function buildScript(page, elapsed) {
  const P = "mb-phone";
  const C = "mb-console";
  const S = [];
  const add = (t, desc, fn) => S.push({ t, desc, fn });

  // ---- S0  public landing -------------------------------------------------
  add(seg("S0"), "landing: load", async () => {
    await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => localStorage.setItem("manobal.language", "en"));
    await injectOverlay(page, CUES, elapsed());
  });
  add(seg("S0", 5), "landing: scroll to the figures", () =>
    page.evaluate(() => window.scrollTo({ top: 780, behavior: "smooth" })));
  add(seg("S0", 9.5), "landing: scroll to the pillars", () =>
    page.evaluate(() => window.scrollTo({ top: 1560, behavior: "smooth" })));
  add(seg("S0", 13), "landing: back to top", () =>
    page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" })));

  // ---- S1  check-in on the phone, welfare queue on the console ------------
  add(seg("S1"), "stage: open phone=/app console=/welfare", async () => {
    await page.goto(`${BASE}/stage?phone=/app&console=/welfare`, { waitUntil: "domcontentloaded" });
    await waitForFrame(page, "mb-phone");
    await waitForFrame(page, "mb-console");
    await injectOverlay(page, CUES, elapsed());
    await waitLoaded(page, C, "a[href^='/welfare/cases/']");
  });
  add(seg("S1", 3.2), "phone: open check-in", async () => {
    await nav(page, P, "/app/check-in");
    await waitLoaded(page, P, ".mb-emoji-row button");
  });
  add(seg("S1", 6.0), "check-in: mood", () => advanceCheckIn(page, { score: 4 }));
  add(seg("S1", 8.0), "check-in: energy", () => advanceCheckIn(page, { score: 3 }));
  add(seg("S1", 9.8), "check-in: sleep", () => advanceCheckIn(page, { score: 2 }));
  add(seg("S1", 11.6), "check-in: tags + continue", () => advanceCheckIn(page));
  add(seg("S1", 13.6), "check-in: save", () => advanceCheckIn(page));

  // ---- S2  Saathi voice, then the language switch -------------------------
  add(seg("S2", 0.5), "phone: open Saathi", async () => {
    await nav(page, P, "/app/saathi");
    await waitLoaded(page, P, "button:has-text('Hold to talk')");
  });
  add(seg("S2", 3.0), "phone: hold to talk", () =>
    click(page, P, "button:has-text('Hold to talk'), button:has-text('Play recorded')",
      "saathi voice button"));
  add(seg("S2", 8.5), "phone: switch to Hindi", () => setPhoneLang(page, "hi"));
  add(seg("S2", 11.5), "phone: back to English", () => setPhoneLang(page, "en"));

  // ---- S3  the case workspace --------------------------------------------
  add(seg("S3", -4.0), "console: open case MB-4091", async () => {
    await nav(page, C, "/welfare/cases/MB-4091");
    await waitLoaded(page, C, "button:has-text('Reveal to contact')", { timeout: 16000 });
  });
  add(seg("S3", 2.0), "phone: toolkit", async () => {
    await nav(page, P, "/app/toolkit");
    await waitLoaded(page, P, "a[href^='/app/toolkit/']");
  });
  add(seg("S3", 6.5), "console: pick the 48-hour rest lever", () =>
    click(page, C, "input[name='lever']", "recommended action radio"));
  add(seg("S3", 9.0), "phone: scroll the practices", () => scrollFrame(page, P, 620));
  add(seg("S3", 12.0), "console: request the sleep trend", () =>
    click(page, C, "button:has-text('Request sleep trend')", "trend sharing"));
  add(seg("S3", 15.0), "phone: scroll further", () => scrollFrame(page, P, 1400));

  // ---- S4  purpose-bound reveal, and the ledger on the phone --------------
  add(seg("S4"), "console: write the care justification", async () => {
    const frame = frameOf(page, C);
    const box = await frame.$("textarea");
    if (!box) throw new Error("reveal: justification textarea missing");
    await box.click();
    await box.type("Care contact after sustained workload and sleep drift.", { delay: 34 });
  });
  add(seg("S4", 5.5), "console: reveal to contact", () =>
    click(page, C, "button:has-text('Reveal to contact')", "reveal button"));
  add(seg("S4", 8.0), "phone: open Me", async () => {
    await nav(page, P, "/app/me");
    await waitLoaded(page, P, "a[href='/app/plan']");
  });
  add(seg("S4", 10.5), "phone: scroll to who viewed my information", () =>
    scrollFrame(page, P, 780));

  // ---- S5  unit posture ---------------------------------------------------
  add(seg("S5", -2.0), "console: unit posture", async () => {
    await nav(page, C, "/command");
    await waitLoaded(page, C, "button:has-text('Ask copilot')");
  });
  add(seg("S5", 4.5), "console: open a suppressed tile", () =>
    click(page, C, "button:has-text('Fewer than 10 people')", "suppressed tile"));
  add(seg("S5", 8.0), "phone: consent receipt", () => scrollFrame(page, P, 1500));
  add(seg("S5", 11.0), "console: a banded tile", () =>
    click(page, C, "button:has-text('20 to 30%')", "banded tile"));

  // ---- S6  the copilot refusal -------------------------------------------
  add(seg("S6", 0.5), "console: open the copilot", () =>
    click(page, C, "button:has-text('Ask copilot')", "ask copilot"));
  add(seg("S6", 3.0), "console: ask who is under strain", () =>
    click(page, C, "button:has-text('Who is under strain?')", "copilot preset"));
  add(seg("S6", 4.2), "console: send it", () =>
    click(page, C, "button:text-is('Ask')", "copilot ask"));
  add(seg("S6", 9.0), "phone: settings", () => scrollFrame(page, P, 2200));

  // ---- S7  roster balancer ------------------------------------------------
  add(seg("S7", -4.0), "console: roster balancer", async () => {
    await nav(page, C, "/command/roster");
    await waitLoaded(page, C, "button:has-text('Project 14 days')");
  });
  add(seg("S7", 3.0), "console: ease the night share", () =>
    click(page, C, "button:has-text('Ease night share')", "ease night share"));
  add(seg("S7", 6.0), "phone: plan my rest", async () => {
    await nav(page, P, "/app/rest");
    await waitLoaded(page, P, "h1");
  });
  add(seg("S7", 8.0), "console: project 14 days", () =>
    click(page, C, "button:has-text('Project 14 days')", "project 14 days"));
  add(seg("S7", 10.5), "console: create the draft order", () =>
    click(page, C, "button:has-text('Create draft order')", "create draft order"));

  // ---- S8  the acute path -------------------------------------------------
  add(seg("S8"), "phone: back to Saathi", async () => {
    await nav(page, P, "/app/saathi");
    await waitLoaded(page, P, "button:has-text('Keyboard')");
  });
  add(seg("S8", 2.2), "phone: switch to the keyboard", () =>
    click(page, P, "button:has-text('Keyboard'), button:has-text('कीबोर्ड')", "keyboard"));
  add(seg("S8", 4.0), "phone: type the acute phrase", async () => {
    const frame = frameOf(page, P);
    // The Saathi input carries no type attribute, so [type='text'] would miss it.
    const input = await frame.waitForSelector("form input", { state: "visible", timeout: 6000 });
    await input.click();
    await input.type("main jeena nahi chahta", { delay: 85 });
  });
  add(seg("S8", 7.5), "phone: send it", async () => {
    const frame = frameOf(page, P);
    const send = await frame.waitForSelector(
      "button:has-text('Send'), button:has-text('भेजें')",
      { state: "visible", timeout: 6000 },
    );
    await send.click({ timeout: 8000 });
  });
  add(seg("S8", 11.0), "phone: confirm the safety screen", async () => {
    const frame = frameOf(page, P);
    await frame.waitForSelector("a[href='tel:14416']", { state: "visible", timeout: 8000 });
  });
  add(seg("S8", 12.5), "phone: the safety screen", () => scrollFrame(page, P, 260));
  add(seg("S8", 15.0), "phone: back to the top of the safety screen", () =>
    scrollFrame(page, P, 0));

  // ---- S9  medical acute board -------------------------------------------
  add(seg("S9", -5.0), "console: acute board", async () => {
    await nav(page, C, "/medical");
    await waitLoaded(page, C, "button:has-text('Acknowledge')");
  });
  add(seg("S9", 4.0), "phone: hold on the safety screen", () =>
    scrollFrame(page, P, 120));

  // ---- S10 counsellor desk -----------------------------------------------
  add(seg("S10", -4.0), "console: counsellor desk", async () => {
    await nav(page, C, "/counsel");
    await waitLoaded(page, C, "button:has-text('Join call')");
  });
  add(seg("S10", 3.0), "console: an anonymous session", () =>
    click(page, C, "button:has-text('Name hidden')", "anonymous session"));
  add(seg("S10", 6.0), "phone: talk to a person", async () => {
    await nav(page, P, "/app/talk");
    await waitLoaded(page, P, "button:has-text('Request')");
  });
  add(seg("S10", 8.5), "phone: scroll the request options", () => scrollFrame(page, P, 420));

  // ---- S11 governance, the audit chain -----------------------------------
  add(seg("S11", -5.0), "console: governance", async () => {
    await nav(page, C, "/governance");
    await waitLoaded(page, C, "button:has-text('Tamper')");
  });
  add(seg("S11", 3.0), "console: verify the chain", () =>
    click(page, C, "button:has-text('Verify')", "verify"));
  add(seg("S11", 7.0), "console: tamper with the chain", () =>
    click(page, C, "button:has-text('Tamper')", "tamper"));
  add(seg("S11", 12.0), "console: restore the chain", () =>
    click(page, C, "button:has-text('Restore')", "restore"));
  add(seg("S11", 15.0), "phone: assessments", async () => {
    await nav(page, P, "/app/assessments");
    await waitLoaded(page, P, "a[href^='/app/assessments/']");
  });

  // ---- S12 DPO centre -----------------------------------------------------
  add(seg("S12", -3.0), "console: DPO centre", async () => {
    await nav(page, C, "/dpo");
    await waitLoaded(page, C, "button:has-text('Publish')");
  });
  add(seg("S12", 3.5), "console: close a rights request", () =>
    click(page, C, "button:has-text('Close')", "rights queue close"));
  add(seg("S12", 6.5), "phone: scroll the assessments", () => scrollFrame(page, P, 500));
  add(seg("S12", 5.5), "console: publish a privacy notice", () =>
    click(page, C, "button:has-text('Publish')", "publish notice"));

  // ---- S13 integrations ---------------------------------------------------
  add(seg("S13", -5.0), "console: integrations", async () => {
    await nav(page, C, "/integrations");
    await waitLoaded(page, C, "button:has-text('Run now')");
  });
  add(seg("S13", 3.5), "console: run the roster feed", () =>
    click(page, C, "button:has-text('Run now')", "run now"));
  add(seg("S13", 5.5), "console: test that names are blocked", () =>
    click(page, C, "button:has-text('Test that names are blocked')", "name block test"));
  add(seg("S13", 9.5), "phone: family connect", async () => {
    await nav(page, P, "/app/family");
    await waitLoaded(page, P, "button:has-text('call')");
  });

  // ---- S14 validation lab -------------------------------------------------
  add(seg("S14", -4.0), "console: validation lab", async () => {
    await nav(page, C, "/lab");
    await waitLoaded(page, C, "button:has-text('Shifted world')");
  });
  add(seg("S14", 4.0), "console: the shifted world", () =>
    click(page, C, "button:has-text('Shifted world')", "shifted world"));
  add(seg("S14", 7.0), "phone: my safety plan", async () => {
    await nav(page, P, "/app/plan");
    await waitLoaded(page, P, "textarea");
  });
  add(seg("S14", 9.5), "console: back to the primary world", () =>
    click(page, C, "button:has-text('Primary world')", "primary world"));
  add(seg("S14", 12.0), "phone: scroll the safety plan", () => scrollFrame(page, P, 320));

  // ---- S15 architecture ---------------------------------------------------
  add(seg("S15", -4.0), "console: architecture", async () => {
    await nav(page, C, "/architecture");
    await waitLoaded(page, C, "button:has-text('Run self-test')");
  });
  add(seg("S15", 4.0), "console: zone 2, patterns", () =>
    click(page, C, "button:has-text('Zone 2')", "zone 2"));
  add(seg("S15", 8.0), "console: zone X, never connected", () =>
    click(page, C, "button:has-text('Zone X')", "zone X"));
  add(seg("S15", 11.5), "console: run the self-test", () =>
    click(page, C, "button:has-text('Run self-test')", "self test"));
  add(seg("S15", 1.0), "phone: a breathing practice", async () => {
    await nav(page, P, "/app/toolkit/breathe");
    await waitLoaded(page, P, "h1");
  });
  add(seg("S15", 9.0), "phone: raise a concern", async () => {
    await nav(page, P, "/app/concerns");
    await waitLoaded(page, P, "button:has-text('Send')");
  });
  add(seg("S15", 13.0), "phone: scroll the concern form", () => scrollFrame(page, P, 260));

  // ---- S16 close ----------------------------------------------------------
  add(seg("S16"), "phone: home", async () => {
    await nav(page, P, "/app");
    await waitLoaded(page, P, "a[href='/app/check-in']");
  });
  add(seg("S16", 4.0), "console: back to the welfare queue", async () => {
    await nav(page, C, "/welfare");
    await waitLoaded(page, C, "a[href^='/welfare/cases/']");
  });
  add(seg("S16", 8.0), "phone: gentle scroll to close", () => scrollFrame(page, P, 300));

  S.sort((a, b) => a.t - b.t);
  return S;
}

/* -------------------------------------------------------------- pre-warm */

async function prewarm(browser) {
  const routes = [
    "/", "/stage?phone=/app&console=/welfare",
    "/app", "/app/check-in", "/app/saathi", "/app/toolkit", "/app/me", "/app/rest",
    "/app/talk", "/app/assessments", "/app/family", "/app/plan", "/app/safety",
    "/welfare", "/welfare/cases/MB-4091", "/command", "/command/roster", "/medical",
    "/counsel", "/governance", "/dpo", "/integrations", "/lab", "/architecture", "/hq",
  ];
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  process.stdout.write("[warm] ");
  for (const r of routes) {
    try {
      await page.goto(BASE + r, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(450);
      process.stdout.write(".");
    } catch {
      process.stdout.write("x");
    }
  }
  // The routes above load unauthenticated, so the signed-in variants never
  // compile. Cycle the console through them inside a real stage session, which
  // is what actually made /medical and /counsel slow in an earlier take.
  try {
    await page.goto(`${BASE}/stage?phone=/app&console=/welfare`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector('iframe[name="mb-console"]', { timeout: 20000 });
    await page.waitForTimeout(7000);
    for (const r of ["/welfare/cases/MB-4091", "/medical", "/counsel", "/governance",
                     "/dpo", "/integrations", "/lab", "/architecture", "/hq",
                     "/command", "/command/roster", "/welfare"]) {
      await page.evaluate(
        (route) => document.querySelector('iframe[name="mb-console"]')
          .contentWindow.location.assign(route), r);
      await page.waitForTimeout(3500);
      process.stdout.write("+");
    }
  } catch (e) {
    process.stdout.write(`x(${e.message.slice(0, 40)})`);
  }
  console.log(" done");
  await ctx.close();
}

/* ------------------------------------------------------------------- main */

async function main() {
  console.log("=".repeat(64));
  console.log(`MANOBAL demo recorder - ${DRY ? "DRY RUN" : "REAL TAKE"} (${TIMELINE.total}s)`);
  console.log("=".repeat(64));

  const outDir = path.join(ROOT, "out");
  fs.mkdirSync(outDir, { recursive: true });

  // Reset the demo world so the take is reproducible.
  try {
    const res = await fetch("http://localhost:8000/api/v1/auth/demo-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "director" }),
    });
    const { access_token } = await res.json();
    for (const ep of ["reset", "warmup"]) {
      await fetch(`http://localhost:8000/api/v1/demo/${ep}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${access_token}` },
      });
    }
    console.log("[preflight] demo world reset + warmed");
  } catch (e) {
    console.warn("[preflight] reset failed (continuing):", e.message);
  }

  CUES = loadCues();
  console.log(`[captions] ${CUES.length} cues loaded`);

  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  await prewarm(browser);

  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    ...(DRY ? {} : { recordVideo: { dir: outDir, size: { width: 1920, height: 1080 } } }),
  });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => log.push(`[pageerror] ${String(e).slice(0, 160)}`));

  let t0 = Date.now();
  const script = buildScript(page, () => (Date.now() - t0) / 1000);
  console.log(`[script] ${script.length} actions across ${TIMELINE.segments.length} segments\n`);

  t0 = Date.now();
  for (const step of script) {
    if (!DRY) {
      const wait = t0 + step.t * 1000 - Date.now();
      if (wait > 0) await page.waitForTimeout(wait);
    }
    const at = ((Date.now() - t0) / 1000).toFixed(2);
    const drift = DRY ? 0 : (Date.now() - t0) / 1000 - step.t;
    const began = Date.now();
    try {
      await step.fn();
      const took = (Date.now() - began) / 1000;
      // A step that takes long enough to eat the next mark is the real danger:
      // it silently compresses whatever follows. Flag it in both modes.
      const slow = took > 1.5 ? `  SLOW ${took.toFixed(2)}s` : "";
      const flag = Math.abs(drift) > 0.6 ? `  DRIFT ${drift > 0 ? "+" : ""}${drift.toFixed(2)}s` : "";
      if (slow) slowSteps.push({ desc: step.desc, took });
      console.log(`  ok   t=${String(step.t).padStart(6)}s (${at}s) ${step.desc}${flag}${slow}`);
    } catch (e) {
      failures.push({ t: step.t, desc: step.desc, error: e.message });
      console.log(`  FAIL t=${String(step.t).padStart(6)}s (${at}s) ${step.desc}\n         ${e.message}`);
    }
  }

  if (!DRY) {
    const remaining = t0 + TIMELINE.total * 1000 - Date.now();
    if (remaining > 0) await page.waitForTimeout(remaining);
  }

  const elapsed = (Date.now() - t0) / 1000;
  const video = DRY ? null : await page.video();
  await ctx.close();
  await browser.close();

  if (video) {
    const dest = path.join(outDir, "manobal_screen_master.webm");
    const src = await video.path();
    fs.copyFileSync(src, dest);
    console.log(`\n[video] ${dest} (${(fs.statSync(dest).size / 1e6).toFixed(1)} MB)`);
  }

  console.log(`\n[elapsed] ${elapsed.toFixed(2)}s`);
  if (log.length) {
    console.log(`[page errors] ${log.length}`);
    for (const l of log.slice(0, 8)) console.log("   ", l);
  }
  if (lateLoads.length) {
    console.log(`\n[late loads] ${lateLoads.length} screen(s) were not ready inside budget:`);
    for (const m of lateLoads) console.log(`   ${m}`);
  }
  if (slowSteps.length) {
    console.log(`\n[slow steps] ${slowSteps.length} took over 1.5s:`);
    for (const s of slowSteps.sort((a, b) => b.took - a.took)) {
      console.log(`   ${s.took.toFixed(2)}s  ${s.desc}`);
    }
  }
  if (failures.length) {
    console.log(`\n${"!".repeat(64)}\n${failures.length} FAILED STEP(S):`);
    for (const f of failures) console.log(`  t=${f.t}s  ${f.desc}\n      ${f.error}`);
    console.log("!".repeat(64));
    process.exit(1);
  }
  console.log("\nAll steps succeeded.");
}

main().catch((e) => {
  console.error("RECORDER CRASHED:", e);
  process.exit(1);
});
