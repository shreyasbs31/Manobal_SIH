import assert from "node:assert/strict";
import test from "node:test";

function slaTone(remainingRatio, tier) {
  if (tier === "T4") {
    return "acute";
  }
  if (remainingRatio < 0.2) {
    return "marigold";
  }
  if (remainingRatio < 0.5) {
    return "brass";
  }
  return "calm";
}

test("SLA colour follows remaining time and T4", () => {
  assert.equal(slaTone(0.8, "T2"), "calm");
  assert.equal(slaTone(0.4, "T2"), "brass");
  assert.equal(slaTone(0.1, "T3"), "marigold");
  assert.equal(slaTone(0.9, "T4"), "acute");
});
