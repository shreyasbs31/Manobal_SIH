import { describe, expect, it } from "vitest";

import {
  buildCheckin,
  buildInstrumentTotal,
  buildJournalCiphertext,
  enrolmentHoldsTokenOnly,
  validateBatch,
} from "../src/protocol";
import { LOCK_SCREEN_BODY, LOCK_SCREEN_URGENT, SCREENS, lockScreenBody } from "../src/screens";
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

  it("syncs a journal as ciphertext only", () => {
    const batch = buildJournalCiphertext({
      subject_token: "tok_1",
      client_batch_id: "j1",
      ciphertext: "YWJj",
      nonce: "bm9uY2U",
      key_id: "jk_1",
    });
    expect(validateBatch(batch)).toBeNull();
    expect(JSON.stringify(batch)).not.toMatch(/body|plaintext|private/);
  });

  it("refuses instrument item answers on the wire", () => {
    const reason = validateBatch({
      subject_token: "tok_1",
      client_batch_id: "i1",
      items: [{ kind: "instrument", answers: [1, 2, 3] } as never],
    });
    expect(reason).toBeTruthy();
    const total = buildInstrumentTotal({
      subject_token: "tok_1",
      client_batch_id: "i2",
      instrument_code: "phq9",
      language: "hi",
      total: 4,
    });
    expect(validateBatch(total)).toBeNull();
    expect(JSON.stringify(total)).not.toMatch(/answers/);
  });

  it("keeps enrolment to a token", () => {
    expect(enrolmentHoldsTokenOnly({ subject_token: "st_abc" })).toBe(true);
    expect(enrolmentHoldsTokenOnly({ subject_token: "st_abc", service_no: "CRPF-1" } as never)).toBe(
      false,
    );
    expect(SCREENS.enrolment.collects).toMatch(/never a service number/);
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
