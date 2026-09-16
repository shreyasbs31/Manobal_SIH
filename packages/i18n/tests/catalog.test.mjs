import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const catalog = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../src/catalog.ts"),
  "utf8",
);

test("reviewed hindi safety title", () => {
  assert.ok(catalog.includes('"safety.title": "आप अकेले नहीं हैं।"'));
});

test("tamil greeting for karthik", () => {
  assert.ok(catalog.includes("வணக்கம், கார்த்திக்"));
});
