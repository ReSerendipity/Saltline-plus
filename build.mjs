/* build.mjs — 把 src/ 源码按占位符拼回单文件 dist/Saltline.html。
 *
 * shell.html 占位符：
 *   <script id="i18n-runtime">/*__I18N__*​/</script>          → src/i18n.js + 道具 i18n 合并片段
 *   <script>/*__VENDOR__*​/ /*__GAME__*​/ /*__GADGETS__*​/</script>
 *       __VENDOR__  → src/vendor/three.min.js（原样，不美化）
 *       __GAME__    → src/game.js（已美化；注意：主脚本是单个大 IIFE，
 *                      "(()=>{" 开头在 vendor 尾部之前、"}())" 结尾在 game 尾部，
 *                      vendor 与 game 必须原序拼接才构成完整脚本）
 *       __GADGETS__ → src/gadgets/{core,emp,smoke,support}.js
 *
 * replace 一律使用函数形式，避免替换串里的 $&、$'、${...} 被当作替换模式转义。
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const read = (p) => readFileSync(join(root, p), "utf8");

const shell = read("src/shell.html");
const i18n = read("src/i18n.js");
const vendor = read("src/vendor/three.min.js");
const game = read("src/game.js");
const gadgetFiles = [
  "src/gadgets/core.js",
  "src/gadgets/emp.js",
  "src/gadgets/smoke.js",
  "src/gadgets/support.js",
];
const gadgets = gadgetFiles.map(read).join("\n;\n");

// 道具与首页公告 i18n：多份 JSON 按语言浅合并为一份字典（en = 键名本身，不需要词条），
// 以 I18N.D 增量补齐的方式追加在 i18n-runtime 脚本之后。
const gadgetI18n = {};
for (const f of ["src/i18n/emp.json", "src/i18n/smoke.json", "src/i18n/support.json", "src/i18n/announce.json", "src/i18n/controls.json"]) {
  const data = JSON.parse(read(f));
  for (const lang of Object.keys(data)) {
    if (!gadgetI18n[lang]) gadgetI18n[lang] = {};
    Object.assign(gadgetI18n[lang], data[lang]);
  }
}
const i18nMerge =
  "\n;(function () {\n" +
  "  try {\n" +
  "    var X = " +
  JSON.stringify(gadgetI18n) +
  ";\n" +
  "    for (var lang in X) {\n" +
  "      if (!window.I18N) break;\n" +
  "      if (!window.I18N.D[lang]) window.I18N.D[lang] = {};\n" +
  "      for (var k in X[lang]) window.I18N.D[lang][k] = X[lang][k];\n" +
  "    }\n" +
  '  } catch (e) { try { console.error("[gadget-i18n] merge failed", e); } catch (_) {} }\n' +
  "})();\n";

let out = shell;
function sub(placeholder, value) {
  const before = out;
  out = out.replace(placeholder, () => value); // 函数形式：防 $& 转义
  if (out === before) throw new Error("placeholder not found: " + placeholder);
}
sub("/*__I18N__*/", i18n + i18nMerge);
sub("/*__VENDOR__*/", vendor);
sub("/*__GAME__*/", game);
sub("/*__GADGETS__*/", gadgets);

if (out.includes("/*__")) throw new Error("unresolved placeholder remains in output");

mkdirSync(join(root, "dist"), { recursive: true });
const distPath = join(root, "dist", "Saltline.html");
writeFileSync(distPath, out);

const size = out.length;
const sha = createHash("sha256").update(out).digest("hex").toUpperCase();
console.log("built dist/Saltline.html");
console.log("  size  :", size, "bytes");
console.log("  sha256:", sha);
console.log("  parts : i18n", i18n.length, "+ vendor", vendor.length, "+ game", game.length, "+ gadgets", gadgets.length);
