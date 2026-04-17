/* eslint-disable no-console */
const fs = require("node:fs");
const path = require("node:path");

if (process.platform !== "win32") process.exit(0);

const viteChunkPath = path.join(
  __dirname,
  "..",
  "node_modules",
  "vite",
  "dist",
  "node",
  "chunks",
  "node.js",
);

if (!fs.existsSync(viteChunkPath)) process.exit(0);

let content = fs.readFileSync(viteChunkPath, "utf8");

if (content.includes('try {\n\t\texec("net use",') || content.includes('try {\r\n\t\texec("net use",'))
  process.exit(0);

const open = '\texec("net use", (error, stdout) => {';
const openIndex = content.indexOf(open);
if (openIndex === -1) process.exit(0);

const afterOpenIndex = openIndex + open.length;

const closeLF = "\t});\n}";
const closeCRLF = "\t});\r\n}";
let closeIndex = content.indexOf(closeCRLF, afterOpenIndex);
let closeToken = closeCRLF;
if (closeIndex === -1) {
  closeIndex = content.indexOf(closeLF, afterOpenIndex);
  closeToken = closeLF;
}
if (closeIndex === -1) process.exit(0);

content =
  content.slice(0, openIndex) +
  '\ttry {\n\t\texec("net use", (error, stdout) => {' +
  content.slice(afterOpenIndex);

const insertedOffset = "\ttry {\n".length;
closeIndex += insertedOffset;

content =
  content.slice(0, closeIndex) +
  "\t\t});\n\t} catch {}\n}" +
  content.slice(closeIndex + closeToken.length);

fs.writeFileSync(viteChunkPath, content, "utf8");
console.log("[postinstall] Patched Vite Windows net-use exec guard");
