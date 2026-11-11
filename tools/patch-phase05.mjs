// 阶段 0.5 共享 AI 钩子补丁（src/game.js，CRLF 安全，唯一锚点断言）。
// 1) Gull x(y) / Hound S(T) 顶部：stunT>0 时递减并短路 AI/移动/转向/开火（死亡残骸在 g/U，不受影响）。
// 2) enemies.think：调用 physics.lineOfSight 前先做线段-烟球相交测试，被烟幕遮挡则 j=false。
// 3) combat 模块新增 emp(pos, radius, duration)：不造成伤害，返回受影响数量。
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

// 1a) Gull 逐帧更新入口 x(y)
patch(
  "gull x(y) stunT short-circuit",
  ["  function x(y) {", "    let b = s.player,", "      m = i.t;"].join(NL),
  [
    "  function x(y) {",
    "    if (d.stunT > 0) {",
    "      d.stunT = Math.max(0, d.stunT - y);",
    "      return",
    "    }",
    "    let b = s.player,",
    "      m = i.t;",
  ].join(NL),
);

// 1b) Hound 逐帧更新入口 S(T)
patch(
  "hound S(T) stunT short-circuit",
  ["  function S(T) {", "    let D = s.player,", "      C = i.t;"].join(NL),
  [
    "  function S(T) {",
    "    if (m.stunT > 0) {",
    "      m.stunT = Math.max(0, m.stunT - T);",
    "      return",
    "    }",
    "    let D = s.player,",
    "      C = i.t;",
  ].join(NL),
);

// 2) enemies.think：烟幕遮挡感知（传感器→玩家眼睛线段与烟球相交则不调用 lineOfSight）
patch(
  "think smoke-blocked line of sight",
  ['              (T.mode === "engage" || ne > BC || F < 3.5) && (j = i.physics.lineOfSight(T.sensor, N))'].join(NL),
  ['              (T.mode === "engage" || ne > BC || F < 3.5) && (j = slSmokeBlocks(i.smokes, T.sensor, N) ? !1 : i.physics.lineOfSight(T.sensor, N))'].join(NL),
);

// 2b) 线段-烟球相交测试（定义在 enemies 模块之前，em/slime 共用）
patch(
  "smoke segment-sphere helper",
  ["async function Em(i) {"].join(NL),
  [
    "function slSmokeBlocks(i, e, t) {",
    "  // 阶段 0.5 共享感知钩子：线段 e→t 与任一烟球（{pos,radius,t}）相交则返回 true",
    "  if (!i || !i.length) return !1;",
    "  let n = e.x - t.x,",
    "    s = e.y - t.y,",
    "    o = e.z - t.z;",
    "  for (let r = 0; r < i.length; r++) {",
    "    let a = i[r];",
    "    if (!a || !a.pos || !(a.radius > 0) || !(a.t > 0)) continue;",
    "    let l = e.x - a.pos.x,",
    "      c = e.y - a.pos.y,",
    "      u = e.z - a.pos.z,",
    "      h = n * n + s * s + o * o,",
    "      f = l * l + c * c + u * u - a.radius * a.radius;",
    "    if (f <= 0) return !0;",
    "    if (h === 0) continue;",
    "    let d = 2 * (l * n + c * s + u * o),",
    "      p = d * d - 4 * h * f;",
    "    if (p < 0) continue;",
    "    let m = (-d - Math.sqrt(p)) / (2 * h);",
    "    if (m >= 0 && m <= 1) return !0",
    "  }",
    "  return !1",
    "}",
    "async function Em(i) {",
  ].join(NL),
);

// 3) combat.emp：范围眩晕钩子（不造成伤害，返回受影响数量）
patch(
  "combat.emp",
  [
    "        l < s && i.physics.lineOfSight(n, nm.copy(a.pos).setY(a.pos.y + 1)) && a.damage(o * .5 * (1 - l / s), n)",
    "      }",
    "    }",
    "  }",
    "}",
  ].join(NL),
  [
    "        l < s && i.physics.lineOfSight(n, nm.copy(a.pos).setY(a.pos.y + 1)) && a.damage(o * .5 * (1 - l / s), n)",
    "      }",
    "    },",
    "    emp(n, s = 8, o = 4) {",
    "      // 阶段 0.5 共享钩子：范围内活敌 stunT = max(stunT, duration)；无伤害。当前代码无精英标记，统一时长。",
    "      let r = 0;",
    "      for (let l of i.enemies.list) {",
    "        if (!l.alive) continue;",
    "        l.pos.distanceTo(n) < s && (l.stunT = Math.max(l.stunT || 0, o), r++)",
    "      }",
    "      return r",
    "    }",
    "  }",
    "}",
  ].join(NL),
);

writeFileSync(file, s);
console.log("game.js phase 0.5 hooks patched OK");
