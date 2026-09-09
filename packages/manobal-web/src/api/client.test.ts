import { describe, expect, it } from "vitest";

import { commanderPayloadHasNoToken } from "./client";

describe("commander payload guard", () => {
  it("accepts a k-anonymised rollup", () => {
    expect(
      commanderPayloadHasNoToken({
        unit: "12BN_A",
        period_start: "2026-09-01",
        period_end: "2026-09-07",
        suppressed: false,
        elevated_band: "1-4",
        dominant_category: "workload_and_duty",
        trend_direction: "stable",
      }),
    ).toBe(true);
  });

  it("rejects a payload that smuggles a subject token", () => {
    expect(
      commanderPayloadHasNoToken({
        unit: "12BN_A",
        period_start: "2026-09-01",
        period_end: "2026-09-07",
        suppressed: false,
        subject_token: "tok_secret",
      } as never),
    ).toBe(false);
  });
});
