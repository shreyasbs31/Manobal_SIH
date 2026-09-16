import assert from "node:assert/strict";
import test from "node:test";

import { soundEnabled, vibrate } from "../src/sound.mjs";

test("sound is off by default", () => {
  assert.equal(soundEnabled(), false);
});

test("vibrate no-ops when navigator is missing", () => {
  assert.doesNotThrow(() => vibrate(8));
});
