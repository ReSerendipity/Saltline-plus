/* gadgets/core.js — Saltline 道具系统核心（阶段 0 脚手架）
 *
 * 运行环境：构建时拼接在主脚本（一个大 IIFE：(()=>{ three.js + game })();）之后，
 * 因此本文件处于顶层作用域，只能通过 window.__G / window.I18N / DOM 与游戏交互。
 *
 * 接口约定（阶段 0）：
 *   window.SaltlineGadgets.register(def)
 *     def = {
 *       id:       string                // 唯一 id，如 "emp"
 *       slot:     0 | 1 | 2             // 槽位；1/2/3 数字键选择
 *       charges:  number                // 初始充能次数，也是补给上限
 *       cooldown: number                // 使用后的冷却秒数（空壳为 0）
 *       nameKey:  string                // i18n 键（英文原文即键，en 无需词条）
 *       icon:     string                // 图标占位（阶段 0 不渲染）
 *       use:      (G, ctx) => boolean   // 使用回调；显式返回 false = 未实现/未消耗
 *       update:   (G, dt, state) => void // 可选：逐帧回调（阶段 0.5b）
 *     }
 *   G 即 window.__G（游戏上下文）；
 *   ctx = { time, player, from, point, dir }，
 *   point = 准星射线 20m 内命中点（无命中则视线前方 20m 处），dir = 视线单位向量。
 *
 * 状态：window.__G.gadgets = {
 *   charges:  { [id]: 剩余次数 }      // 初始 emp2 smoke2 decoy1 ammo1 stim1
 *   selected: 当前选中道具 id
 *   select(i) 选择槽位 i（再次选择同槽位时在槽内循环切换，如 decoy→ammo→stim）
 *   use()     使用当前选中的道具
 *   update(dt) 逐帧推进：冷却递减、Q（现有 alt 动作）触发使用、
 *             敌人 stunT 字段预留、烟幕数据结构空更新
 *   refill(n) 全部道具 +n，不超过初始（中继切断后由 objective:done 事件触发 refill(1)）
 * }
 *
 * 阶段 0.5：烟幕/眩晕为共享数据钩子（__G.smokes 生命期管理、敌人 stunT 字段
 * 预留），感知遮挡与范围眩晕的游戏侧实现见 game.js 的 think()/combat.emp。
 * 阶段 0 明确不做：EMP/烟幕/支援的实际效果、触屏按钮。
 */
(function () {
  "use strict";
  if (window.SaltlineGadgets) return; // 幂等：防止脚本被注入两次

  var SLOTS = 3;
  var defs = []; // 注册顺序
  var byId = {};

  // ------------------------------------------------------------------ 状态
  var state = {
    charges: {}, // id -> 剩余次数
    max: {}, // id -> 上限（= 注册时的初始 charges）
    cooldown: {}, // id -> 剩余冷却秒
    selected: null, // 当前选中道具 id
    selBySlot: [null, null, null], // 每个槽位当前指向的道具 id
    defs: defs,
    select: select,
    use: use,
    update: update,
    refill: refill,
  };

  // ------------------------------------------------------------------ 注册
  function register(def) {
    if (!def || typeof def.id !== "string" || !def.id)
      throw new Error("[gadgets] register: def.id (string) required");
    if (!(def.slot >= 0 && def.slot < SLOTS))
      throw new Error("[gadgets] register " + def.id + ": slot must be 0..2");
    if (typeof def.nameKey !== "string" || !def.nameKey)
      throw new Error("[gadgets] register " + def.id + ": nameKey required");
    def.charges = def.charges | 0;
    if (def.charges < 0) def.charges = 0;
    def.cooldown = +def.cooldown || 0;
    if (typeof def.use !== "function") def.use = function () { return !1; };

    if (byId[def.id]) {
      // 同 id 重注册：替换定义，保留已累积的状态
      defs[defs.indexOf(byId[def.id])] = def;
    } else {
      defs.push(def);
      state.charges[def.id] = def.charges;
      state.max[def.id] = def.charges;
      state.cooldown[def.id] = 0;
      if (!state.selBySlot[def.slot]) state.selBySlot[def.slot] = def.id;
    }
    byId[def.id] = def;
    if (!state.selected) state.selected = def.id;
    if (booted) hudSync();
  }

  var api = {
    register: register,
    state: state, // 调试直通（正式状态以 window.__G.gadgets 为准）
  };
  window.SaltlineGadgets = api;

  // ------------------------------------------------------------------ 行为
  function select(i) {
    if (!(i >= 0 && i < SLOTS)) return;
    var items = [];
    for (var k = 0; k < defs.length; k++) if (defs[k].slot === i) items.push(defs[k]);
    if (!items.length) return;
    if (state.selected === state.selBySlot[i] && items.length > 1) {
      // 同槽位再按一次：槽内循环切换（decoy → ammo → stim）
      var idx = -1;
      for (var j = 0; j < items.length; j++) if (items[j].id === state.selBySlot[i]) idx = j;
      state.selBySlot[i] = items[(idx + 1) % items.length].id;
    }
    state.selected = state.selBySlot[i];
    hudSync();
    var def = byId[state.selected];
    var G = window.__G;
    if (G && def) say(G, I18N.t(def.nameKey) + " \u00d7" + state.charges[state.selected], 1.5);
  }

  function use() {
    var G = window.__G;
    if (!G) return;
    var id = state.selected;
    var def = id && byId[id];
    if (!def) return;
    if ((state.charges[id] | 0) <= 0) {
      say(G, I18N.t(def.nameKey) + " \u2014 " + I18N.t("No charges left"), 1.8);
      return;
    }
    if ((state.cooldown[id] || 0) > 0) {
      say(G, I18N.t(def.nameKey) + " \u2014 " + I18N.t("Cooling down"), 1.2);
      return;
    }
    var ctx = { time: G.time, player: G.player, from: "player" };
    // 阶段 0.5b 共享接口：瞄准点 = 准星射线 20m 内命中点，否则视线前方 20m 处
    try {
      var dir = new G.THREE.Vector3();
      G.camera.getWorldDirection(dir);
      var eye = G.camera.position.clone();
      var hit = G.physics.raycast(eye, dir, 20);
      ctx.point = hit && hit.point ? hit.point : eye.clone().addScaledVector(dir, 20);
      ctx.dir = dir;
    } catch (e) {
      console.error("[gadgets] aim point failed", e);
    }
    var consumed;
    try {
      consumed = def.use(G, ctx);
    } catch (e) {
      console.error("[gadgets] use " + id + " threw", e);
      consumed = false;
    }
    if (consumed === false) {
      // 空壳约定：显式返回 false = 本版本未实装，不消耗充能
      say(G, I18N.t(def.nameKey) + " \u2014 " + I18N.t("not wired in this build"), 2);
      return;
    }
    state.charges[id] = Math.max(0, state.charges[id] - 1);
    state.cooldown[id] = def.cooldown || 0;
    hudSync();
  }

  function update(dt) {
    var G = window.__G;
    if (!G) return;
    dt = +dt || 0;
    var cooling = false;
    for (var id in state.cooldown) {
      if (state.cooldown[id] > 0) {
        state.cooldown[id] = Math.max(0, state.cooldown[id] - dt);
        cooling = true;
      }
    }
    // 输入：Q = 现有 alt 动作（键位表中 KeyQ:"alt"，当前无其他消费者）
    try {
      if (G.input && typeof G.input.pressed === "function" && G.input.pressed("alt")) state.use();
    } catch (e) { /* 输入子系统未就绪时静默 */ }
    // 敌人 stunT 字段预留（眩晕钩子，阶段 0 只保证字段存在）
    var list = G.enemies && G.enemies.list;
    if (list) {
      for (var k = 0; k < list.length; k++) {
        var en = list[k];
        if (en && en.stunT === undefined) en.stunT = 0;
      }
    }
    // 烟幕共享钩子（阶段 0.5）：t 递减、到期移除；上限 4 个，超出移除最旧。
    // 烟球形状 { pos:{x,y,z}, radius, t }；游戏侧 think() 用它做视线遮挡。
    var smokes = G.smokes;
    if (smokes) {
      for (var s = smokes.length - 1; s >= 0; s--) {
        var sm = smokes[s];
        if (!sm) continue;
        sm.t = (sm.t || 0) - dt;
        if (sm.t <= 0) smokes.splice(s, 1);
      }
      while (smokes.length > 4) smokes.shift();
    }
    // 阶段 0.5b 共享接口：道具自定义逐帧更新（def.update(G, dt, state)）
    for (var di = 0; di < defs.length; di++) {
      var dfn = defs[di];
      if (typeof dfn.update === "function") {
        try {
          dfn.update(G, dt, state);
        } catch (e) {
          console.error("[gadgets] def.update " + dfn.id + " threw", e);
        }
      }
    }
    if (cooling) hudSync();
  }

  function refill(n) {
    n = n | 0;
    if (n <= 0) return;
    for (var i = 0; i < defs.length; i++) {
      var id = defs[i].id;
      if (state.charges[id] < state.max[id])
        state.charges[id] = Math.min(state.max[id], state.charges[id] + n);
    }
    hudSync();
  }

  function say(G, text, secs) {
    try {
      if (G.hud && typeof G.hud.message === "function") G.hud.message(text, secs || 2);
    } catch (e) { /* HUD 未就绪时静默 */ }
  }

  // ------------------------------------------------------------------ HUD
  // .h-gadget：三个槽位 chip（键位 / 名称 / 次数 / 选中态），插在 .h-ammo 上方
  var hud = null;

  function buildHud() {
    if (hud) return;
    var ammo = document.querySelector(".hud .h-ammo") || document.querySelector(".h-ammo");
    if (!ammo || !ammo.parentNode) return;
    var root = document.createElement("div");
    root.className = "h-gadget";
    root.setAttribute("aria-hidden", "true");
    var head = document.createElement("div");
    head.className = "h-k";
    head.textContent = I18N.t("Gadget");
    var row = document.createElement("div");
    row.className = "h-gadget-row";
    root.appendChild(head);
    root.appendChild(row);
    hud = { root: root, row: row, chips: [] };
    ammo.parentNode.insertBefore(root, ammo);
  }

  function hudSync() {
    if (!hud) return;
    for (var slot = 0; slot < SLOTS; slot++) {
      var chip = hud.chips[slot];
      if (!chip) {
        chip = document.createElement("span");
        chip.className = "g-chip";
        hud.row.appendChild(chip);
        hud.chips[slot] = chip;
      }
      var id = state.selBySlot[slot];
      var def = id && byId[id];
      var cls = "g-chip";
      if (def) {
        if (state.selected === id) cls += " sel";
        if ((state.charges[id] | 0) <= 0) cls += " empty";
        if ((state.cooldown[id] || 0) > 0) cls += " cooling";
        chip.innerHTML =
          '<b class="g-key">' + (slot + 1) + "</b>" +
          '<span class="g-name"></span>' +
          '<em class="g-n">\u00d7' + state.charges[id] + "</em>";
        chip.querySelector(".g-name").textContent = I18N.t(def.nameKey);
      } else {
        chip.innerHTML = '<b class="g-key">' + (slot + 1) + "</b>" + '<span class="g-name">\u2014</span>';
      }
      chip.className = cls;
    }
  }

  // ------------------------------------------------------------------ 启动
  var booted = false;

  function boot(G) {
    if (booted) return;
    booted = true;
    G.gadgets = state; // 调试钩子：window.__G.gadgets
    G.smokes = []; // 烟幕数据结构占位（阶段 0）
    if (!state.selected) state.selected = state.selBySlot[0];

    // 中继切断补给：objective:done 每切断一条中继触发一次
    try {
      G.events.on("objective:done", function () {
        state.refill(1);
      });
    } catch (e) {
      console.error("[gadgets] subscribe objective:done failed", e);
    }

    // 逐帧更新：包装 input.endFrame（在游戏清除 pressed 状态之前执行）
    var origEndFrame = G.input.endFrame;
    G.input.endFrame = function () {
      try {
        state.update((G.time && G.time.dt) || 0);
      } catch (e) {
        console.error("[gadgets] update threw", e);
      }
      if (typeof origEndFrame === "function") origEndFrame();
    };

    // 1/2/3 选择槽位（游戏键位表未占用数字键）
    addEventListener(
      "keydown",
      function (e) {
        var t = e.target;
        if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) return;
        var slot = -1;
        if (e.code === "Digit1" || e.code === "Numpad1") slot = 0;
        else if (e.code === "Digit2" || e.code === "Numpad2") slot = 1;
        else if (e.code === "Digit3" || e.code === "Numpad3") slot = 2;
        if (slot < 0 || e.repeat) return;
        if (!G.game || G.game.state !== "playing") return;
        e.preventDefault();
        state.select(slot);
      },
      !0
    );

    buildHud();
    hudSync();
  }

  // 轮询等待游戏上下文就绪（__G 在主脚本同步赋值，但 hud/enemies 等模块异步挂载）
  ;(function waitBoot() {
    var tries = 0;
    var timer = setInterval(function () {
      tries++;
      var G = window.__G;
      if (G && G.input && G.events && G.hud && G.enemies && G.game && G.time) {
        clearInterval(timer);
        try {
          boot(G);
        } catch (e) {
          console.error("[gadgets] boot failed", e);
        }
      } else if (tries > 1000) {
        clearInterval(timer);
        console.error("[gadgets] game context not ready, giving up");
      }
    }, 60);
  })();
})();
