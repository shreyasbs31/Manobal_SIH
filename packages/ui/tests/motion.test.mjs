import assert from "node:assert/strict";
import test from "node:test";

import { MOTION, motionToOpacityOnly } from "../src/motion-tokens.mjs";

test("named motion tokens exist", () => {
  for (const name of ["instant", "quick", "settle", "draw", "breath"]) {
    assert.ok(name in MOTION);
  }
});

test("reduced motion falls back to a short opacity change", () => {
  const next = motionToOpacityOnly(true, "draw");
  assert.equal(next.duration, 120);
  assert.notEqual(next.duration, MOTION.draw.duration);
});
