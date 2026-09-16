import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const required = [
  "MB-4091",
  "MB-2217",
  "MB-3380",
  "MB-1506",
  "MB-5120",
  "MB-6604",
  "MB-7342",
  "MB-8815",
];

test("ui fixtures use spec 29 persona ids", () => {
  const source = readFileSync(new URL("../src/ui-fixtures.ts", import.meta.url), "utf8");
  for (const id of required) {
    assert.match(source, new RegExp(id));
  }
  assert.match(source, /REST_48H/);
  assert.match(source, /Bn C-02/);
});
