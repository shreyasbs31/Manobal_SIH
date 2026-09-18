import assert from "node:assert/strict";
import test from "node:test";

import {
  BOX_BREATH_PATTERN,
  BREATH_SCALE_MAX,
  BREATH_SCALE_MIN,
  FOUR_SEVEN_EIGHT_PATTERN,
  MOTION,
  breathPhaseAt,
  breathScaleAt,
  motionToOpacityOnly,
} from "../src/motion-tokens.mjs";

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

test("box breath expands then holds without snapping the count", () => {
  const start = breathPhaseAt(0, BOX_BREATH_PATTERN);
  assert.equal(start.id, "in");
  assert.equal(start.count, 4);
  assert.equal(start.expand, true);
  const lateInhale = breathPhaseAt(3500, BOX_BREATH_PATTERN);
  assert.equal(lateInhale.id, "in");
  assert.equal(lateInhale.count, 1);
  const hold = breathPhaseAt(4500, BOX_BREATH_PATTERN);
  assert.equal(hold.id, "hold-in");
  assert.equal(hold.expand, true);
  assert.equal(hold.hold, true);
  const exhale = breathPhaseAt(9000, BOX_BREATH_PATTERN);
  assert.equal(exhale.id, "out");
  assert.equal(exhale.expand, false);
  const loop = breathPhaseAt(16000, BOX_BREATH_PATTERN);
  assert.equal(loop.id, "in");
});

test("box breath scale holds large then contracts without a snap", () => {
  assert.ok(Math.abs(breathScaleAt(0, BOX_BREATH_PATTERN) - BREATH_SCALE_MIN) < 0.001);
  assert.ok(breathScaleAt(2000, BOX_BREATH_PATTERN) > 0.95);
  assert.ok(breathScaleAt(2000, BOX_BREATH_PATTERN) < 1.1);
  assert.ok(Math.abs(breathScaleAt(4000, BOX_BREATH_PATTERN) - BREATH_SCALE_MAX) < 0.001);
  assert.ok(Math.abs(breathScaleAt(6000, BOX_BREATH_PATTERN) - BREATH_SCALE_MAX) < 0.001);
  assert.ok(Math.abs(breathScaleAt(8000, BOX_BREATH_PATTERN) - BREATH_SCALE_MAX) < 0.001);
  const midOut = breathScaleAt(10000, BOX_BREATH_PATTERN);
  assert.ok(midOut > 0.9);
  assert.ok(midOut < 1.08);
  assert.ok(Math.abs(breathScaleAt(12000, BOX_BREATH_PATTERN) - BREATH_SCALE_MIN) < 0.001);
  assert.ok(Math.abs(breathScaleAt(14000, BOX_BREATH_PATTERN) - BREATH_SCALE_MIN) < 0.001);
  assert.ok(Math.abs(breathScaleAt(16000, BOX_BREATH_PATTERN) - BREATH_SCALE_MIN) < 0.001);
  const seams = [4000, 8000, 12000, 16000];
  for (const seam of seams) {
    assert.ok(Math.abs(breathScaleAt(seam - 1, BOX_BREATH_PATTERN) - breathScaleAt(seam, BOX_BREATH_PATTERN)) < 0.02);
  }
});

test("4-7-8 scale holds then takes the longer exhale", () => {
  assert.ok(Math.abs(breathScaleAt(4000, FOUR_SEVEN_EIGHT_PATTERN) - BREATH_SCALE_MAX) < 0.001);
  assert.ok(Math.abs(breathScaleAt(8000, FOUR_SEVEN_EIGHT_PATTERN) - BREATH_SCALE_MAX) < 0.001);
  const midOut = breathScaleAt(15000, FOUR_SEVEN_EIGHT_PATTERN);
  assert.ok(midOut > BREATH_SCALE_MIN);
  assert.ok(midOut < BREATH_SCALE_MAX);
  assert.ok(Math.abs(breathScaleAt(19000, FOUR_SEVEN_EIGHT_PATTERN) - BREATH_SCALE_MIN) < 0.001);
});
