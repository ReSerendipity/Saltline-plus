/* verify.mjs — 阶段 0 静态验收检查（浏览器运行时验证另做）。
 * 检查项：原文件哈希未变（原文件不存在时跳过）/ node --check / dist 存在且 >1.4MB / 占位符已替换 /
 *         SaltlineGadgets 接口 / 初始 charges / h-gadget / overscroll-behavior /
 *         mousedown 不再提前 return / 主脚本拼接完整性。
 * 退出码：全部通过 = 0；任一失败 = 1。 */
import { readFileSync, writeFileSync, statSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const read = (p) => readFileSync(join(root, p), "utf8");
const ORIGINAL = process.env.SALTLINE_ORIGINAL || "";
const BASE_SHA = "BAA1E58FA480877DF7EF317C06A44CFDEC2F7D61F61025BA7D0162B2B088E5C2";

const results = [];
function check(name, ok, detail) {
  results.push(ok);
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (detail ? "  -- " + detail : ""));
}
function nodeCheckAbs(p) {
  try {
    execFileSync(process.execPath, ["--check", p], { stdio: "pipe" });
    return true;
  } catch (e) {
    return String(e.stderr || e.message);
  }
}
const nodeCheck = (p) => nodeCheckAbs(join(root, p));

// ---- 1. 原文件基线未动（可选：设置 SALTLINE_ORIGINAL 指向原始单文件时校验）----
if (ORIGINAL && existsSync(ORIGINAL)) {
  const origSha = createHash("sha256").update(readFileSync(ORIGINAL)).digest("hex").toUpperCase();
  check("original SHA256 unchanged", origSha === BASE_SHA, origSha);
} else {
  check("original file not present — baseline hash check skipped", true, ORIGINAL || "SALTLINE_ORIGINAL unset");
}

// ---- 2. 可独立解析的源文件 ----------------------------------------------
for (const p of [
  "src/i18n.js",
  "src/gadgets/core.js",
  "src/gadgets/emp.js",
  "src/gadgets/smoke.js",
  "src/gadgets/support.js",
]) {
  const r = nodeCheck(p);
  check("node --check " + p, r === true, r === true ? undefined : String(r).split("\n").slice(-3).join(" ").slice(0, 140));
}

// ---- 3. game.js = 主 IIFE 片段（单独 check 必失败且为片段特征；与 vendor 拼接后必须通过）
{
  const r = nodeCheck("src/game.js");
  const fragmentOk = r !== true && /Unexpected token '\}'|end of input/i.test(String(r));
  check(
    "src/game.js is a fragment of the single main IIFE (standalone check fails as expected)",
    fragmentOk,
    r === true ? "unexpectedly parsed standalone" : String(r).split("\n").slice(-3).join(" ").slice(0, 140)
  );
  const concat = read("src/vendor/three.min.js") + read("src/game.js");
  const tmp = join(tmpdir(), "saltline-main-check.js");
  writeFileSync(tmp, concat);
  const r2 = nodeCheckAbs(tmp);
  check("node --check vendor+game (full main script)", r2 === true, r2 === true ? undefined : String(r2).split("\n").slice(-3).join(" ").slice(0, 140));
}

// ---- 4. dist 产物 -------------------------------------------------------
const distPath = join(root, "dist", "Saltline.html");
let distOk = true;
try {
  statSync(distPath);
} catch {
  distOk = false;
}
check("dist/Saltline.html exists", distOk);
const dist = distOk ? read("dist/Saltline.html") : "";
const distSize = distOk ? statSync(distPath).size : 0;
check("dist size > 1.4MB (1,400,000 bytes)", distSize > 1400000, distSize + " bytes");

// ---- 5. 占位符已替换 ----------------------------------------------------
for (const ph of ["/*__I18N__*/", "/*__VENDOR__*/", "/*__GAME__*/", "/*__GADGETS__*/"]) {
  check("placeholder replaced: " + ph, distOk && !dist.includes(ph));
}

// ---- 6. gadget 核心 ------------------------------------------------------
check("window.SaltlineGadgets defined in dist", dist.includes("window.SaltlineGadgets"));
check("__G.gadgets exposed in dist", dist.includes("G.gadgets = state"));
check("__G.smokes placeholder in dist", dist.includes("G.smokes = []"));
check("enemy stunT reservation in dist", dist.includes("stunT"));
check("h-gadget node in dist", dist.includes('className = "h-gadget"') && dist.includes(".h-gadget {"));
check("refill capped at initial in dist", dist.includes("refill") && dist.includes("state.max[id]"));

// 初始充能（各空壳文件内的 def 字段）
const chargesSpec = [
  ["src/gadgets/emp.js", /id:\s*"emp"/, /charges:\s*2/],
  ["src/gadgets/smoke.js", /id:\s*"smoke"/, /charges:\s*2/],
  ["src/gadgets/support.js", /id:\s*"decoy"/, /charges:\s*1/],
  ["src/gadgets/support.js", /id:\s*"ammo"/, /charges:\s*1/],
  ["src/gadgets/support.js", /id:\s*"stim"/, /charges:\s*1/],
];
for (const [file, idRe, chRe] of chargesSpec) {
  const src = read(file);
  check(`initial charges def in ${file} (${idRe})`, idRe.test(src) && chRe.test(src));
}
check(
  "all five gadget defs present in dist",
  ["emp", "smoke", "decoy", "ammo", "stim"].every((id) => new RegExp('id:\\s*"' + id + '"').test(dist))
);

// ---- 7. i18n JSON（三份文件按语言合并后须覆盖 5 个道具名，zh/ja/ko 齐全）----
{
  const need = ["EMP", "Smoke", "Decoy", "Ammo Box", "Stim"];
  let ok = true;
  let detail = "";
  try {
    const merged = {};
    for (const f of ["src/i18n/emp.json", "src/i18n/smoke.json", "src/i18n/support.json"]) {
      const data = JSON.parse(read(f));
      for (const lang of Object.keys(data)) {
        if (!data[lang] || typeof data[lang] !== "object") throw new Error(f + " lang " + lang + " not an object");
        if (!merged[lang]) merged[lang] = {};
        Object.assign(merged[lang], data[lang]);
      }
    }
    for (const lang of ["zh", "ja", "ko"]) {
      if (!merged[lang]) throw new Error("missing lang " + lang);
      for (const k of need) {
        if (merged[lang][k] === undefined) throw new Error("missing key " + JSON.stringify(k) + " for " + lang);
      }
    }
  } catch (e) {
    ok = false;
    detail = String(e.message || e);
  }
  check("gadget i18n JSONs valid (zh/ja/ko, 5 names merged)", ok, detail);
  check("gadget i18n merged into dist", dist.includes("gadget-i18n") && dist.includes("EMP \u8109\u51b2\u96f7"));
}

// ---- 8. 右键修复 --------------------------------------------------------
// 8a. mousedown：请求锁定后不再提前 return
check(
  "mousedown: no early return after requesting pointer lock",
  /A\(\), P\.preventDefault\(\)\s*\}\s*u \|= 1 << P\.button/.test(dist),
);
check(
  "mousedown: old early-return pattern removed",
  !/A\(\), P\.preventDefault\(\);\s*return/.test(dist),
);
// 8b. window 捕获阶段拦截右键
check(
  "window capture: gameplay right-button mousedown preventDefault",
  /addEventListener\("mousedown", P => \{\s*P\.button === 2 && r && P\.preventDefault\(\)\s*\}, !0\)/.test(dist),
);
check(
  "window capture: gameplay contextmenu preventDefault",
  /addEventListener\("contextmenu", P => \{\s*r && P\.preventDefault\(\)\s*\}, !0\)/.test(dist),
);
// 8c. CSS overscroll
check("css overscroll-behavior: none on html, body", /html, body \{[^}]*overscroll-behavior:\s*none;/.test(dist));

// ---- 9. dist 主脚本 = vendor + game + gadgets（字节级完整性） --------------
{
  const gadgetsJoin = [
    read("src/gadgets/core.js"),
    read("src/gadgets/emp.js"),
    read("src/gadgets/smoke.js"),
    read("src/gadgets/support.js"),
  ].join("\n;\n");
  const expected = read("src/vendor/three.min.js") + " " + read("src/game.js") + " " + gadgetsJoin;
  const tagAt = dist.lastIndexOf("<script>");
  const closeAt = dist.indexOf("</script>", tagAt);
  const main = tagAt >= 0 && closeAt > tagAt ? dist.slice(tagAt + 8, closeAt) : null;
  check("dist main script bytes == vendor + game + gadgets", main === expected, main ? "length " + main.length + " vs " + expected.length : "script not found");
  if (main !== null) {
    const tmp = join(tmpdir(), "saltline-dist-main-check.js");
    writeFileSync(tmp, main);
    const r = nodeCheckAbs(tmp);
    check("node --check dist main script", r === true, r === true ? undefined : String(r).split("\n").slice(-3).join(" ").slice(0, 140));
  }
}

// ---- 结果 ----------------------------------------------------------------
const failed = results.filter((x) => !x).length;
console.log("\n" + (results.length - failed) + "/" + results.length + " checks passed" + (failed ? ", " + failed + " FAILED" : ""));
process.exitCode = failed ? 1 : 0;
