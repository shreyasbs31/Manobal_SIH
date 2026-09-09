import { describe, expect, it } from "vitest";

import { buildCheckin, validateBatch } from "../src/protocol";
import { LOCK_SCREEN_BODY, LOCK_SCREEN_URGENT, lockScreenBody } from "../src/screens";
import { syncBatch } from "../src/sync";
import { triage } from "../src/triage";

describe("device protocol", () => {
  it("refuses identifying fields", () => {
    const reason = validateBatch({
      subject_token: "tok_1",
      client_batch_id: "b1",
      items: [{ kind: "bio", service_no: "CRPF-1" } as never],
    });
    expect(reason).toBeTruthy();
  });

  it("builds a check-in without free text", () => {
    const batch = buildCheckin({
      subject_token: "tok_1",
      client_batch_id: "b2",
      mood: 3,
      sleep_quality: 2,
      stress: 4,
      connection: 3,
    });
    expect(validateBatch(batch)).toBeNull();
    expect(JSON.stringify(batch)).not.toMatch(/service_no|full_name/);
  });

  it("keeps lock-screen copy to the two published sentences", () => {
    expect(lockScreenBody(false)).toBe(LOCK_SCREEN_BODY);
    expect(lockScreenBody(true)).toBe(LOCK_SCREEN_URGENT);
    expect(LOCK_SCREEN_BODY).toBe("MANOBAL: 1 welfare item needs your review.");
    expect(LOCK_SCREEN_URGENT).toBe("MANOBAL: 1 urgent welfare item needs your review.");
  });

  it("holds crisis language on the device", () => {
    const result = triage("I want to die");
    expect(result.crisis).toBe(true);
    expect(result.holdOnDevice).toBe(true);
  });

  it("does not sync a dirty batch", async () => {
    const result = await syncBatch(
      {
        subject_token: "",
        client_batch_id: "x",
        items: [],
      },
      { edgeUrl: "http://edge", token: "t" },
    );
    expect(result.accepted).toBe(false);
    expect(result.status).toBe(422);
  });
});
