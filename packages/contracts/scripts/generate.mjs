#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const specPath = resolve(here, "../../../services/engine/openapi.json");
const outPath = resolve(here, "../src/schema.ts");

const spec = JSON.parse(readFileSync(specPath, "utf8"));
const ast = await openapiTS(spec);
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(
  outPath,
  `/**\n * Generated from services/engine/openapi.json. Do not edit.\n */\n${astToString(ast)}`,
  "utf8",
);
console.log(outPath);
