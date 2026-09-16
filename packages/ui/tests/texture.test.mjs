import assert from "node:assert/strict";
import test from "node:test";

import { contourPaths, contourSvg, hashSeed } from "../src/texture.mjs";

test("the same seed yields the same contour paths", () => {
  const a = contourPaths({ seed: "MB-4091" });
  const b = contourPaths({ seed: "MB-4091" });
  assert.equal(a.length, b.length);
  assert.ok(a.length >= 6);
  assert.deepEqual(
    a.map((path) => path.d),
    b.map((path) => path.d),
  );
});

test("a different seed yields a different contour", () => {
  const a = contourPaths({ seed: "MB-4091" })[3]?.d;
  const b = contourPaths({ seed: "MB-6604" })[3]?.d;
  assert.ok(a);
  assert.ok(b);
  assert.notEqual(a, b);
});

test("hashSeed is stable", () => {
  assert.equal(hashSeed("Arjun"), hashSeed("Arjun"));
  assert.notEqual(hashSeed("Arjun"), hashSeed("Deepak"));
});

test("contourSvg emits path elements", () => {
  const svg = contourSvg("MB-4091", 120, 80);
  assert.match(svg, /<path /);
  assert.doesNotMatch(svg, /camouflage|flag|crest/i);
});
