import assert from "node:assert/strict";
import test from "node:test";

import { soundEnabled, vibrate } from "../src/sound.mjs";

test("sound is off by default", () => {
  assert.equal(soundEnabled(), false);
});

test("vibrate no-ops when navigator is missing", () => {
  assert.doesNotThrow(() => vibrate(8));
});

test("console queue chimes T4 first then T3", async () => {
  const { chimeKindForQueue } = await import("../src/sound.mjs");
  assert.equal(chimeKindForQueue(1, 4), "t4");
  assert.equal(chimeKindForQueue(0, 2), "t3");
  assert.equal(chimeKindForQueue(0, 0), "");
});
