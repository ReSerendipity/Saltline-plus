/* gadgets/emp.js — EMP 脉冲雷（阶段 1 Track A）。
 * use() 在瞄准点引爆：8m 内活敌 stunT = max(stunT, 4s)，无伤害；
 * 触发火花/冷蓝闪光/离子烟与耳鸣音效，HUD 播报眩晕数；
 * 返回 true 消耗一枚充能（n 为 0 也消耗）。 */
(function () {
  "use strict";
  var api = window.SaltlineGadgets;
  if (!api) {
    console.error("[gadgets] emp.js: core.js must be concatenated before this file");
    return;
  }
  api.register({
    id: "emp",
    slot: 0,
    charges: 2,
    cooldown: 1.2,
    nameKey: "EMP",
    icon: "EMP",
    use: function (G, ctx) {
      var p = ctx && ctx.point;
      if (!p || !isFinite(p.x) || !isFinite(p.y) || !isFinite(p.z)) return false;
      if (!G.combat || typeof G.combat.emp !== "function") return false;
      var n = G.combat.emp(p, 8, 4);
      // 视觉：上冲火花 + 冷蓝闪光 + 短促离子烟
      G.fx.sparks(p, new G.THREE.Vector3(0, 1, 0), 24);
      G.render.lightPool.flash(p, 0x66ccff, 30, 12, .15);
      G.fx.smoke(p, { size: .8, life: 1.2, rise: .5, color: 0x9fd8ff, count: 6, alpha: .25 });
      // 音频：耳鸣（ear_ring 为 dry 总线一次性音效，pos 不参与定位，gain 生效）
      G.audio.play("ear_ring", { pos: p, gain: .7 });
      G.hud.message(I18N.t("EMP pulse — {0} stunned", n), 1.8);
      return true;
    },
  });
})();
