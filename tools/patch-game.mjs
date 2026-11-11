// 阶段 0 右键瞄准修复补丁（对 src/game.js 应用，CRLF 安全，幂等性由唯一模式匹配保证）。
// 1) mousedown：pointer lock 未获时请求锁定后不再 return，让右键首次按下即写入 ads。
// 2) window 捕获阶段：gameplay 时拦截右键 mousedown 与 contextmenu 的默认行为。
import { readFileSync, writeFileSync } from "node:fs";

const file = new URL("../src/game.js", import.meta.url);
let s = readFileSync(file, "utf8");
const NL = "\r\n";

function count(hay, needle) {
  return hay.split(needle).length - 1;
}
function patch(name, from, to) {
  const c = count(s, from);
  if (c !== 1) {
    console.error(`patch "${name}": expected exactly 1 occurrence, found ${c}`);
    process.exit(1);
  }
  s = s.replace(from, to);
  console.log(`patched: ${name}`);
}

// 1) mousedown：去掉提前 return
patch(
  "mousedown no-early-return",
  [
    '      if (!f.locked && f.mode === "lock") {',
    "        A(), P.preventDefault();",
    "        return",
    "      }",
  ].join(NL),
  [
    '      if (!f.locked && f.mode === "lock") {',
    "        A(), P.preventDefault()",
    "      }",
  ].join(NL),
);

// 2) window 捕获阶段监听（复用 v_ 闭包内的 gameplay 标志 r）
patch(
  "window capture preventDefault",
  [
    '  }), addEventListener("contextmenu", P => {',
    "    (P.target === e || r) && P.preventDefault()",
    '  }), addEventListener("mousemove", P => {',
  ].join(NL),
  [
    '  }), addEventListener("contextmenu", P => {',
    "    (P.target === e || r) && P.preventDefault()",
    '  }), addEventListener("mousedown", P => {',
    "    P.button === 2 && r && P.preventDefault()",
    '  }, !0), addEventListener("contextmenu", P => {',
    "    r && P.preventDefault()",
    "  }, !0), addEventListener(\"mousemove\", P => {",
  ].join(NL),
);

writeFileSync(file, s);
console.log("game.js patched OK");
