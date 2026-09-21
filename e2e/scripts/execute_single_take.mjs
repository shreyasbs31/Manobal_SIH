import { chromium } from "@playwright/test";
import { execSync } from "child_process";
import fs from "fs";
import path from "path";

async function injectOverlay(page) {
  await page.evaluate(() => {
    if (document.getElementById("demo-overlay-layer")) return;
    const overlay = document.createElement("div");
    overlay.id = "demo-overlay-layer";
    overlay.style.position = "fixed";
    overlay.style.inset = "0";
    overlay.style.pointerEvents = "none";
    overlay.style.zIndex = "9999999";
    overlay.style.fontFamily = "Helvetica, Arial, system-ui, sans-serif";
    overlay.innerHTML = `
      <div id="overlay-persistent" style="position:absolute; bottom:16px; left:24px; font-size:14px; font-weight:600; letter-spacing:0.5px; color:rgba(255,255,255,0.7); background:rgba(0,0,0,0.65); padding:6px 12px; border-radius:4px; backdrop-filter:blur(4px);">
        PROTOTYPE · SYNTHETIC DATA
      </div>
      <div id="overlay-designtarget" style="position:absolute; bottom:16px; right:24px; font-size:14px; font-weight:600; letter-spacing:0.5px; color:rgba(255,255,255,0.7); background:rgba(0,0,0,0.65); padding:6px 12px; border-radius:4px; backdrop-filter:blur(4px); display:none;">
        DESIGN TARGET · SDD v1.0
      </div>
      <div id="overlay-seeded" style="position:absolute; top:72px; left:50%; transform:translateX(-50%); font-size:16px; font-weight:600; color:rgba(255,255,255,0.95); background:rgba(190,35,35,0.88); padding:8px 20px; border-radius:6px; box-shadow:0 4px 12px rgba(0,0,0,0.3); display:none;">
        Seeded acute case, shown to illustrate the Welfare and Medical view.
      </div>
    `;
    document.body.appendChild(overlay);
  });
}

async function updateOverlay(page, elapsedSeconds) {
  const dtVisible =
    (elapsedSeconds >= 37 && elapsedSeconds <= 43) ||
    (elapsedSeconds >= 48 && elapsedSeconds <= 58) ||
    (elapsedSeconds >= 129 && elapsedSeconds <= 134) ||
    (elapsedSeconds >= 166 && elapsedSeconds <= 171) ||
    (elapsedSeconds >= 210 && elapsedSeconds <= 222);

  const seededVisible = elapsedSeconds >= 150 && elapsedSeconds <= 165;

  await page
    .evaluate(
      ({ dt, seeded }) => {
        const dtEl = document.getElementById("overlay-designtarget");
        const seededEl = document.getElementById("overlay-seeded");

        if (dtEl) dtEl.style.display = dt ? "block" : "none";
        if (seededEl) seededEl.style.display = seeded ? "block" : "none";
      },
      { dt: dtVisible, seeded: seededVisible },
    )
    .catch(() => {});
}

async function executeTake() {
  console.log("==================================================");
  console.log("MANOBAL Feature-Complete Autonomous Recorder (240.0s)");
  console.log("==================================================");

  const outDir = path.resolve("out");
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  // Preflight reset and warmup
  console.log("[PREFLIGHT] Triggering backend reset and warmup via director API...");
  try {
    const tokenRes = execSync(
      `curl -s -X POST http://localhost:8000/api/v1/auth/demo-login -H "Content-Type: application/json" -d '{"role":"director"}'`,
    ).toString();
    const token = JSON.parse(tokenRes).access_token;
    execSync(`curl -s -X POST http://localhost:8000/api/v1/demo/reset -H "Authorization: Bearer ${token}"`);
    execSync(`curl -s -X POST http://localhost:8000/api/v1/demo/warmup -H "Authorization: Bearer ${token}"`);
    console.log("[PREFLIGHT] Reset and warmup succeeded.");
  } catch (err) {
    console.error("[PREFLIGHT WARNING] Reset/warmup call failed:", err.message);
  }

  console.log("[BROWSER] Launching Chromium 1920x1080 with video capture...");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: {
      dir: outDir,
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();

  const t0 = Date.now();
  console.log(`[TIMELINE] Capture started at t0 = ${new Date(t0).toISOString()}`);

  const overlayTimer = setInterval(() => {
    const elapsed = (Date.now() - t0) / 1000;
    updateOverlay(page, elapsed);
  }, 100);

  async function at(markSeconds, actionFn, description) {
    const targetMs = t0 + markSeconds * 1000;
    const now = Date.now();
    const waitMs = targetMs - now;
    if (waitMs > 0) {
      await new Promise((r) => setTimeout(r, waitMs));
    } else {
      console.warn(`[TIMELINE DRIFT] Delay at t=${markSeconds}s: ${-waitMs}ms`);
    }
    const elapsed = ((Date.now() - t0) / 1000).toFixed(3);
    console.log(`[t=${elapsed}s / Mark ${markSeconds}s] Action: ${description}`);
    if (actionFn) {
      try {
        await actionFn();
      } catch (err) {
        console.error(`[ACTION ERROR at t=${elapsed}s] ${description}:`, err.message);
      }
    }
  }

  // --- Segment 1: Public Landing & Promise (t=0.0 to t=15.0) ---
  await at(0.0, async () => {
    await page.goto("http://localhost:3000/", { waitUntil: "domcontentloaded" });
    await injectOverlay(page);
  }, "Initial load of public landing page http://localhost:3000/");

  await at(6.0, async () => {
    await page.evaluate(() => window.scrollBy({ top: 750, behavior: "smooth" }));
  }, "Scroll down to MHA statistics figures block on landing page");

  await at(11.0, async () => {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  }, "Scroll back up to core pillars on landing page");

  // --- Segment 2: Stage Entry & Personnel Phone Check-in (t=15.0 to t=35.0) ---
  await at(15.0, async () => {
    await page.goto(
      "http://localhost:3000/stage?phone=/app/check-in&console=/welfare&shot=checkin",
      { waitUntil: "domcontentloaded" },
    );
    await injectOverlay(page);
  }, "Navigate to Stage URL (Check-in & Welfare Queue)");

  let phoneFrame = null;
  let consoleFrame = null;

  await at(17.5, async () => {
    await page.waitForSelector('iframe[name="mb-phone"]', { timeout: 10000 });
    await page.waitForSelector('iframe[name="mb-console"]', { timeout: 10000 });
    phoneFrame = page.frame({ name: "mb-phone" });
    consoleFrame = page.frame({ name: "mb-console" });
    console.log("   Frames resolved cleanly: Phone and Console frame mounted.");
  }, "Verify both Stage frames mounted");

  await at(20.0, async () => {
    if (!phoneFrame) return;
    const moodBtn = (await phoneFrame.$$("button"))[2];
    if (moodBtn) await moodBtn.click();
  }, "Phone: Select mood option");

  await at(22.0, async () => {
    if (!phoneFrame) return;
    const energyBtn = (await phoneFrame.$$("button"))[2];
    if (energyBtn) await energyBtn.click();
  }, "Phone: Select energy option");

  await at(24.0, async () => {
    if (!phoneFrame) return;
    const sleepBtn = (await phoneFrame.$$("button"))[2];
    if (sleepBtn) await sleepBtn.click();
  }, "Phone: Select sleep option");

  await at(26.0, async () => {
    if (!phoneFrame) return;
    const dutyTag = await phoneFrame.$("button:has-text('Duty'), button:has-text('ड्यूटी')");
    if (dutyTag) await dutyTag.click();
  }, "Phone: Select Duty tag");

  await at(27.5, async () => {
    if (!phoneFrame) return;
    const familyTag = await phoneFrame.$("button:has-text('Family'), button:has-text('परिवार')");
    if (familyTag) await familyTag.click();
  }, "Phone: Select Family tag");

  await at(29.0, async () => {
    if (!phoneFrame) return;
    const continueBtn = await phoneFrame.$("button:has-text('Continue'), button:has-text('आगे')");
    if (continueBtn) await continueBtn.click();
  }, "Phone: Click Continue");

  await at(31.5, async () => {
    if (!phoneFrame) return;
    const saveBtn = await phoneFrame.$("button:has-text('Save'), button:has-text('सहेजें')");
    if (saveBtn) await saveBtn.click();
  }, "Phone: Click Save check-in");

  // --- Segment 3: Voice Native Feature on App (t=35.0 to t=55.0) ---
  await at(35.0, async () => {
    if (!phoneFrame) return;
    const saathiNav = await phoneFrame.$("a[href='/app/saathi'], button:has-text('Saathi')");
    if (saathiNav) await saathiNav.click();
  }, "Phone: Navigate to Saathi Companion page (/app/saathi)");

  await at(40.0, async () => {
    if (!phoneFrame) return;
    const holdBtn = await phoneFrame.$("button:has-text('Hold to talk'), button:has-text('Play recorded check-in')");
    if (holdBtn) await holdBtn.click();
  }, "Phone: Trigger Voice check-in / Mic Contour Waveform animation");

  await at(48.0, async () => {
    if (!phoneFrame) return;
    await phoneFrame.evaluate(() => window.scrollBy({ top: 200, behavior: "smooth" }));
  }, "Phone: View live transcript stream and Audio Cleared privacy seal");

  // --- Segment 4: Welfare Queue & Case Workspace (t=55.0 to t=75.0) ---
  await at(55.0, async () => {
    if (!consoleFrame) return;
    const caseCard = await consoleFrame.$("text=MB-4091");
    if (caseCard) await caseCard.click();
  }, "Console: Click MB-4091 case card in Welfare Queue");

  await at(62.0, async () => {
    if (!consoleFrame) return;
    await consoleFrame.evaluate(() => window.scrollBy({ top: 300, behavior: "smooth" }));
  }, "Console: Scroll through 7 contributing domains breakdown");

  await at(68.0, async () => {
    if (!consoleFrame) return;
    await consoleFrame.evaluate(() => window.scrollBy({ top: 350, behavior: "smooth" }));
  }, "Console: View AI recommended action and case brief");

  // --- Segment 5: Purpose-Bound Reveal & Phone Access Ledger (t=75.0 to t=95.0) ---
  await at(75.0, async () => {
    if (!phoneFrame) return;
    const meNav = await phoneFrame.$("a[href='/app/me'], button:has-text('Me')");
    if (meNav) await meNav.click();
  }, "Phone: Navigate to Me page (/app/me)");

  await at(79.0, async () => {
    if (!phoneFrame) return;
    await phoneFrame.evaluate(() => window.scrollBy({ top: 350, behavior: "smooth" }));
  }, "Phone: Scroll to Who viewed my information access ledger");

  await at(83.0, async () => {
    if (!consoleFrame) return;
    const input = await consoleFrame.$("textarea, input[name='reason']");
    if (input) await input.focus();
  }, "Console: Focus justification input field");

  await at(85.0, async () => {
    if (!consoleFrame) return;
    const input = await consoleFrame.$("textarea, input[name='reason']");
    if (input) {
      await input.fill("Care contact after sustained sleep and workload drift.");
    }
  }, "Console: Enter care purpose justification");

  await at(89.0, async () => {
    if (!consoleFrame) return;
    const revealBtn = await consoleFrame.$(
      "button:has-text('Reveal'), button:has-text('Reveal to contact')",
    );
    if (revealBtn) await revealBtn.click();
  }, "Console: Click Reveal to contact button");

  // --- Segment 6: Unit Posture & Roster Balancer (t=95.0 to t=115.0) ---
  await at(95.0, async () => {
    if (!consoleFrame) return;
    const cmdNav = await consoleFrame.$(
      "a[href='/command'], button:has-text('Unit posture'), button:has-text('Command')",
    );
    if (cmdNav) await cmdNav.click();
  }, "Console: Navigate to Unit posture (/command)");

  await at(105.0, async () => {
    if (!consoleFrame) return;
    const rosterNav = await consoleFrame.$(
      "a[href='/command/roster'], button:has-text('Roster balancer')",
    );
    if (rosterNav) await rosterNav.click();
  }, "Console: Navigate to Roster balancer (/command/roster)");

  // --- Segment 7: Command AI Copilot Privacy Boundary (t=115.0 to t=135.0) ---
  await at(115.0, async () => {
    if (!consoleFrame) return;
    const copilotBtn = await consoleFrame.$(
      "button:has-text('Ask copilot'), button:has-text('Copilot')",
    );
    if (copilotBtn) await copilotBtn.click();
  }, "Console: Open Ask Copilot panel");

  await at(118.0, async () => {
    if (!consoleFrame) return;
    const presetBtn = await consoleFrame.$(
      "button:has-text('Who is under strain?')",
    );
    if (presetBtn) await presetBtn.click();
  }, "Console: Click copilot query 'Who is under strain?'");

  // --- Segment 8: Deterministic Acute Safety & Tele-MANAS (t=135.0 to t=155.0) ---
  await at(135.0, async () => {
    if (!phoneFrame) return;
    const saathiNav = await phoneFrame.$("a[href='/app/saathi'], button:has-text('Saathi')");
    if (saathiNav) await saathiNav.click();
  }, "Phone: Navigate to Saathi page");

  await at(138.0, async () => {
    if (!phoneFrame) return;
    const kbBtn = await phoneFrame.$(
      "button:has-text('Keyboard'), button:has-text('कीबोर्ड')",
    );
    if (kbBtn) await kbBtn.click();
  }, "Phone: Click Keyboard button");

  await at(140.0, async () => {
    if (!phoneFrame) return;
    const input = await phoneFrame.$("input[type='text'], textarea");
    if (input) {
      await input.fill("main jeena nahi chahta");
    }
  }, "Phone: Type acute distress phrase 'main jeena nahi chahta'");

  await at(143.0, async () => {
    if (!phoneFrame) return;
    const sendBtn = await phoneFrame.$("button:has-text('Send'), button:has-text('भेजें')");
    if (sendBtn) await sendBtn.click();
  }, "Phone: Click Send button");

  await at(148.0, async () => {
    if (!phoneFrame) return;
    await phoneFrame.evaluate(() => window.scrollBy({ top: 300, behavior: "smooth" }));
  }, "Phone: Scroll down Safety screen (Tele-MANAS 14416)");

  // --- Segment 9: Acute Board & Counsellor Desk (t=155.0 to t=175.0) ---
  await at(155.0, async () => {
    if (!consoleFrame) return;
    const medicalNav = await consoleFrame.$(
      "a[href='/medical'], button:has-text('Acute board'), button:has-text('Medical')",
    );
    if (medicalNav) await medicalNav.click();
  }, "Console: Navigate to Acute board (/medical)");

  await at(165.0, async () => {
    if (!consoleFrame) return;
    const counselNav = await consoleFrame.$(
      "a[href='/counsel'], button:has-text('Counsellor desk')",
    );
    if (counselNav) await counselNav.click();
  }, "Console: Navigate to Counsellor desk (/counsel)");

  // --- Segment 10: Force HQ & DPO Centre (t=175.0 to t=195.0) ---
  await at(175.0, async () => {
    if (!consoleFrame) return;
    const hqNav = await consoleFrame.$(
      "a[href='/hq'], button:has-text('Force HQ')",
    );
    if (hqNav) await hqNav.click();
  }, "Console: Navigate to Force HQ (/hq)");

  await at(185.0, async () => {
    if (!consoleFrame) return;
    const dpoNav = await consoleFrame.$(
      "a[href='/dpo'], button:has-text('DPO centre')",
    );
    if (dpoNav) await dpoNav.click();
  }, "Console: Navigate to DPO centre (/dpo)");

  // --- Segment 11: Adversarial Governance & Audit Chain (t=195.0 to t=215.0) ---
  await at(195.0, async () => {
    if (!consoleFrame) return;
    const govNav = await consoleFrame.$(
      "a[href='/governance'], button:has-text('Governance')",
    );
    if (govNav) await govNav.click();
  }, "Console: Navigate to Governance (/governance)");

  await at(201.0, async () => {
    if (!consoleFrame) return;
    const tamperBtn = await consoleFrame.$("button:has-text('Tamper')");
    if (tamperBtn) await tamperBtn.click();
  }, "Console: Click Tamper button (Audit break detection)");

  await at(206.0, async () => {
    if (!consoleFrame) return;
    const restoreBtn = await consoleFrame.$("button:has-text('Restore')");
    if (restoreBtn) await restoreBtn.click();
  }, "Console: Click Restore button (Audit chain healing)");

  // --- Segment 12: Validation Lab & Closing (t=215.0 to t=240.0) ---
  await at(215.0, async () => {
    if (!consoleFrame) return;
    const labNav = await consoleFrame.$(
      "a[href='/lab'], button:has-text('Validation lab')",
    );
    if (labNav) await labNav.click();
  }, "Console: Navigate to Validation lab (/lab)");

  await at(225.0, async () => {
    if (!consoleFrame) return;
    await consoleFrame.evaluate(() => window.scrollBy({ top: 350, behavior: "smooth" }));
  }, "Console: Scroll down to lead-time and excluded attributes panels");

  await at(240.0, async () => {
    console.log("[TIMELINE COMPLETE] Reached 240.000s mark.");
  }, "Closing 240s mark");

  clearInterval(overlayTimer);

  console.log("[BROWSER] Closing browser context and saving video...");
  const pageVideo = page.video();
  await context.close();
  await browser.close();

  if (pageVideo) {
    const videoPath = await pageVideo.path();
    const targetMaster = path.join(outDir, "manobal_screen_master.webm");
    fs.copyFileSync(videoPath, targetMaster);
    console.log(`[CAPTURE SAVED] Master webm video saved to: ${targetMaster}`);
  }
}

executeTake().catch((err) => {
  console.error("Take failed:", err);
  process.exit(1);
});
