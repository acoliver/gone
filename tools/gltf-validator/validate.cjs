#!/usr/bin/env node
"use strict";
// Scratch validator wrapper for the gone issue #45 pipeline smoke: runs the
// official Khronos glTF-Validator npm build (same version threedee pins,
// 2.0.0-dev.3.10) over a GLB and writes the full report JSON. Mirrors
// threedee's scripts/validate-gltf.cjs options (no timestamp, no external
// resources). Exits 1 only on validator ERRORS; warnings are printed and
// recorded but do not fail the pipeline smoke.
const fs = require("node:fs");
const validator = require("gltf-validator");

async function main() {
  const [input, reportPath] = process.argv.slice(2);
  if (!input || !reportPath || process.argv.length !== 4) {
    console.error("usage: validate.cjs <input.glb> <report.json>");
    process.exit(2);
  }
  const data = fs.readFileSync(input);
  const report = await validator.validateBytes(new Uint8Array(data), {
    uri: input,
    format: "glb",
    maxIssues: 10000,
    writeTimestamp: false,
    externalResourceFunction: (uri) =>
      Promise.reject(new Error(`external resource unavailable: ${uri}`)),
  });
  if (report.issues?.truncated !== false) {
    throw new Error("validator issue report is incomplete");
  }
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
  const issues = report.issues || {};
  const errors = issues.numErrors || 0;
  const warnings = issues.numWarnings || 0;
  console.log(`VALIDATOR errors=${errors} warnings=${warnings}`);
  for (const message of issues.messages || []) {
    console.log(`${message.severity === 0 ? "ERROR" : "WARNING"} ${message.code} ${message.message}`);
  }
  process.exitCode = errors === 0 ? 0 : 1;
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(2);
});
