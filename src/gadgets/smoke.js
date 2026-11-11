/* gadgets/smoke.js — 烟幕罐（阶段 1 Track B）。
 * use()：在准星落点（ctx.point）部署烟球：push 进 G.smokes（形状 { pos, radius, t, puffT }，
 *   生命期 t 的递减/到期移除/上限 4 由 core.js 统一管理，本文件不碰 s.t），
 *   随后触发初始爆发烟 + container_bang 落罐音效 + HUD 提示，return true 消耗充能。
 * update()：按 puffT 节奏为每个存活烟球补冒小团烟，维持烟柱的体积感。
 * 感知遮挡由游戏侧 slSmokeBlocks（game.js think()）读取 G.smokes 实现，本文件只供数据。 */
(function () {
  "use strict";
  var api = window.SaltlineGadgets;
  if (!api) {
    console.error("[gadgets] smoke.js: core.js must be concatenated before this file");
    return;
  }
  api.register({
    id: "smoke",
    slot: 1,
    charges: 2,
    cooldown: 0,
    nameKey: "Smoke",
    icon: "SMK",
    use: function (G, ctx) {
      var p = ctx && ctx.point;
      if (!p || typeof p.x !== "number" || typeof p.y !== "number" || typeof p.z !== "number" ||
        !isFinite(p.x) || !isFinite(p.y) || !isFinite(p.z)) return false;
      if (!G.smokes) return false; // core 未就绪（boot 前 use 不可达，防御性兜底）
      var pos = { x: p.x, y: p.y, z: p.z };
      G.smokes.push({ pos: pos, radius: 4, t: 9, puffT: 0 });
      try {
        G.fx.smoke(p, { size: 1.6, life: 2, rise: .5, color: 0xcfd6d8, count: 10, alpha: .35 });
      } catch (e) { console.error("[gadgets] smoke burst fx failed", e); }
      try {
        G.audio.play("container_bang", { pos: pos, gain: .8 });
      } catch (e) { console.error("[gadgets] smoke audio failed", e); }
      try {
        G.hud.message(I18N.t("Smoke") + " \u2014 " + I18N.t("9s"), 1.5);
      } catch (e) { /* HUD 未就绪时静默 */ }
      return true;
    },
    update: function (G, dt, state) {
      var smokes = G.smokes;
      if (!smokes) return;
      for (var i = 0; i < smokes.length; i++) {
        var s = smokes[i];
        if (!s || !s.pos) continue;
        s.puffT = (s.puffT || 0) - dt;
        if (s.puffT <= 0) {
          try {
            G.fx.smoke({ x: s.pos.x, y: s.pos.y, z: s.pos.z }, { size: 1.4, life: 2.2, rise: .35, color: 0xcfd6d8, count: 1, alpha: .28 });
          } catch (e) { console.error("[gadgets] smoke puff fx failed", e); }
          s.puffT = .22;
        }
      }
    },
  });
})();
