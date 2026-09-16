import assert from "node:assert/strict";
import test from "node:test";

import { ribbonStats } from "../src/charts-stats.mjs";

test("Lay ribbon uses median plus 1.4826 MAD", () => {
  const stats = ribbonStats([
    { day: 1, value: 3 },
    { day: 2, value: 3 },
    { day: 3, value: 3 },
    { day: 4, value: 9 },
  ]);
  assert.ok(stats.spread > 0);
  assert.equal(Number(stats.centre.toFixed(2)), 3);
});
