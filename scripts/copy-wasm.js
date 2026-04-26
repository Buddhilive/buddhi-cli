// Copies LiteRT WASM binaries from node_modules to public/ so they can be
// served locally by Next.js (avoids CDN dependency at runtime).
// Run automatically via the postinstall npm script.

const { cpSync, mkdirSync } = require("fs");
const path = require("path");

const src = path.resolve(__dirname, "../node_modules/@litertjs/core/wasm");
const dest = path.resolve(__dirname, "../public/litert-wasm");

mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });

console.log("✓ LiteRT WASM files copied to public/litert-wasm/");
