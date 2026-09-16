import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const galleryComponents = [
  "TierBadge",
  "TrajectoryArrow",
  "LimitedDataTag",
  "DomainChip",
  "DriverList",
  "BaselineRibbonChart",
  "FormationGrid",
  "HiddenTile",
  "SlaTimer",
  "EscalationLadder",
  "CaseCard",
  "LeverOption",
  "BriefPanel",
  "ConsentToggleCard",
  "ReceiptCard",
  "AccessLedgerItem",
  "AuditRow",
  "ChainStatus",
  "KpiTile",
  "FairnessBar",
  "ReliabilityChart",
  "PhoneFrame",
  "OfflineChip",
  "SyncQueueIndicator",
  "AudioClearedChip",
  "VoiceOrb",
  "CaptionStream",
  "SOSButton",
  "EmojiScale",
  "LanguageGrid",
  "ValidatedBadge",
  "MachineTranslatedBadge",
  "ModeChip",
  "SimClock",
  "EmptyState",
  "ErrorState",
  "ProviderBadge",
  "ZoneDiagram",
  "CallPanel",
  "SafetyPlanEditor",
  "LeaveWindowPicker",
  "ShiftTimeline",
] as const;

const screenshotPages = [
  "/",
  "/login",
  "/app",
  "/app/saathi",
  "/app/toolkit",
  "/app/me",
  "/command",
  "/welfare",
  "/medical",
  "/stage",
  "/dev/components",
] as const;

test("gallery shows every design-system component", async ({ page }) => {
  await page.goto("/dev/components");
  for (const name of galleryComponents) {
    await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  }
  for (const label of [
    "Saathi light",
    "Saathi dark",
    "Saathi high contrast",
    "Command dark",
    "Command light",
  ]) {
    await expect(page.getByRole("button", { name: label })).toBeVisible();
  }
});

test("gallery has no axe violations", async ({ page }) => {
  await page.goto("/dev/components", { waitUntil: "domcontentloaded" });
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("saathi and command shells navigate", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/app", { waitUntil: "domcontentloaded" });
  await page.getByRole("navigation", { name: "Saathi" }).getByRole("link", { name: "Saathi" }).click();
  await expect(page).toHaveURL(/\/app\/saathi/);
  await page.getByRole("link", { name: "Toolkit" }).click();
  await expect(page).toHaveURL(/\/app\/toolkit/);
  await page.goto("/command", { waitUntil: "domcontentloaded" });
  await page.locator('a[href="/welfare"]').click();
  await expect(page).toHaveURL(/\/welfare/);
});

test("stage split view uses query params", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("/stage?phone=/app/saathi&console=/welfare", {
    waitUntil: "domcontentloaded",
  });
  await expect(page.locator('iframe[title="Saathi"]')).toHaveAttribute(
    "src",
    "/app/saathi",
  );
  await expect(page.locator('iframe[title="Command console"]')).toHaveAttribute(
    "src",
    "/welfare",
  );
});

for (const route of screenshotPages) {
  test(`screenshot ${route}`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(route);
    const slug = route === "/" ? "landing" : route.replaceAll("/", "_").slice(1);
    await page.screenshot({
      path: `artifacts/${slug}.png`,
      fullPage: true,
    });
  });
}
