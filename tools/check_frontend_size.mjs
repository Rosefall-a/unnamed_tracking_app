import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../src/frontend/src");
const inventory = [];
async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) await inspect(filename);
    else if (/\.(vue|[cm]?[jt]sx?|css)$/.test(entry.name)) {
      const contents = await readFile(filename, "utf8");
      inventory.push({ file: path.relative(root, filename).replaceAll(path.sep, "/"), lines: contents.split("\n").length - Number(contents.endsWith("\n")) });
    }
  }
}
await inspect(root);
const oversized = inventory.filter(({ lines }) => lines > 2000);
assert.equal(oversized.length, 0, `Frontend files exceed 2,000 lines:\n${oversized.map(({ file, lines }) => `${file}: ${lines}`).join("\n")}`);
inventory.sort((left, right) => right.lines - left.lines);
console.log(`${inventory.length} frontend source files fit the 2,000-line limit; largest ${inventory[0].file}: ${inventory[0].lines}.`);
