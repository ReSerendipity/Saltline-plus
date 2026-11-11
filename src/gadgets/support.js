/* gadgets/support.js — 支援类道具（阶段 1 Track C：诱饵/弹药/医疗实装）。
 * decoy（诱饵信标）/ ammo（弹药箱）/ stim（医疗针）同属槽位 2，
 * 重复按 3 在槽内循环切换（由 core.js 的 select() 处理）。 */
(function () {
  "use strict";
  var api = window.SaltlineGadgets;
  if (!api) {
    console.error("[gadgets] support.js: core.js must be concatenated before this file");
    return;
  }

  // 诱饵共享状态：放置一次，8 秒内每 1 秒向周围 14m 敌人广播一次假警报。
  // pos 为普通 {x,y,z}（敌人 alert() 只做距离平方比较与 copy，无需 Vector3）。
  var decoy = null;

  api.register({
    id: "decoy",
    slot: 2,
    charges: 1,
    cooldown: 0,
    nameKey: "Decoy",
    icon: "DCY",
    use: function (G, ctx) {
      decoy = { pos: { x: ctx.point.x, y: ctx.point.y, z: ctx.point.z }, t: 8, next: 0 };
      G.hud.message(I18N.t("Decoy") + " \u2014 " + I18N.t("8s"), 1.5);
      return true;
    },
    // 逐帧推进（core.js update 阶段回调）：倒计时 + 周期性广播
    update: function (G, dt) {
      if (!decoy) return;
      decoy.t -= dt;
      decoy.next -= dt;
      if (decoy.next <= 0) {
        G.enemies.alert(decoy.pos, 14);
        decoy.next = 1;
      }
      if (decoy.t <= 0) decoy = null;
    },
  });
  api.register({
    id: "ammo",
    slot: 2,
    charges: 1,
    cooldown: 0,
    nameKey: "Ammo Box",
    icon: "AMO",
    use: function (G, ctx) {
      G.weapon.addAmmo(60);
      G.hud.message(I18N.t("Ammo Box") + " +60", 1.5);
      return true;
    },
  });
  api.register({
    id: "stim",
    slot: 2,
    charges: 1,
    cooldown: 0,
    nameKey: "Stim",
    icon: "STM",
    use: function (G, ctx) {
      G.player.heal(50);
      G.hud.message(I18N.t("Stim") + " +50", 1.5);
      return true;
    },
  });
})();
