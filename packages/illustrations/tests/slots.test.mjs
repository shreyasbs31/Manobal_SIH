import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const expected = [
  "bunkDawn",
  "highPost",
  "jungleCamp",
  "cityNight",
  "familyCall",
  "buddyTea",
  "sleepWindDown",
  "informalWalk",
  "counsellorCall",
  "leaveWindow",
  "shiftMoon",
  "onboardingPhone",
  "emptyPath",
  "circleSupport",
];

test("illustration kit exports fourteen typed slots", () => {
  const source = readFileSync(new URL("../src/scenes.tsx", import.meta.url), "utf8");
  const scenes = [...source.matchAll(/export function Scene[A-Za-z]+/g)];
  assert.equal(scenes.length, 14);
  for (const slot of expected) {
    assert.match(source, new RegExp(`${slot}: Scene`));
  }
});
