"""Phase 3B independent verification: fixed turret."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

URL = "http://127.0.0.1:8767/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

LEVEL_TURRETS = """() => {
  const G = window.__G;
  const list = G.enemies.list.filter(e => e.type === 'turret');
  window.__telegraphs = 0; window.__fires = 0; window.__kills = 0;
  G.events.on('enemy:telegraph', e => { if (e.enemy && e.enemy.type === 'turret') window.__telegraphs++; });
  G.events.on('enemy:fire', e => { if (e.enemy && e.enemy.type === 'turret') window.__fires++; });
  G.events.on('enemy:killed', e => { if (e.type === 'turret') window.__kills++; });
  return {
    pool: G.enemies.debug.turrets.length,
    alive: list.length,
    states: list.map(e => ({ x: +e.pos.x.toFixed(1), z: +e.pos.z.toFixed(1), alive: e.alive, visible: e.group.visible })),
    errors: (window.__errors || []).slice(0, 5)
  };
}"""

SETUP = """() => {
  const G = window.__G;
  G.enemies.clear();
  const base = G.player.pos.clone();
  const turret = G.enemies.spawn('turret', new G.THREE.Vector3(base.x + 10, 0, base.z), { yaw: 0 });
  window.__t = turret;
  window.__telegraphs = 0; window.__fires = 0; window.__kills = 0;
  G.events.on('enemy:telegraph', e => { if (e.enemy === turret) window.__telegraphs++; });
  G.events.on('enemy:fire', e => { if (e.enemy === turret) window.__fires++; });
  G.events.on('enemy:killed', e => { if (e.enemy === turret) window.__kills++; });
  return {
    spawned: !!turret, type: turret && turret.type, active: turret && turret.active, alive: turret && turret.alive,
    hp: turret && turret.hp, visible: turret && turret.group.visible,
    yaw0: turret && +turret.yaw.toFixed(3),
    playerHp: G.player.health, errors: (window.__errors || []).slice(0, 5)
  };
}"""

TRACK = """() => {
  const G = window.__G, t = window.__t;
  const want = Math.atan2(G.player.pos.x - t.pos.x, G.player.pos.z - t.pos.z);
  let d = ((t.yaw - want) % (Math.PI * 2));
  if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2;
  return { yaw: +t.yaw.toFixed(3), want: +want.toFixed(3), diff: +d.toFixed(3),
           telegraphs: window.__telegraphs, fires: window.__fires, playerHp: G.player.health };
}"""

FRONT = """() => {
  const t = window.__t; t.hp = 300;
  const y = t.yaw;
  t.damage(100, t.pos.clone(), new window.__G.THREE.Vector3(-Math.sin(y), 0, -Math.cos(y)), 'body');
  return { hp: t.hp, part: 'body' };
}"""

BACK = """() => {
  const t = window.__t; t.hp = 300;
  const y = t.yaw;
  t.damage(100, t.pos.clone(), new window.__G.THREE.Vector3(Math.sin(y), 0, Math.cos(y)), 'body');
  return { hp: t.hp };
}"""

WEAK = """() => {
  const t = window.__t; t.hp = 300;
  const y = t.yaw;
  t.damage(100, t.pos.clone(), new window.__G.THREE.Vector3(Math.sin(y), 0, Math.cos(y)), 'weak');
  return { hp: t.hp };
}"""

EMP = """() => {
  const G = window.__G, t = window.__t;
  const n = G.combat.emp(t.pos.clone(), 8, 4);
  window.__fires = 0; window.__telegraphs = 0;
  t.cool = 0.2; t.firing = false;
  return { affected: n, stunT: t.stunT, headZ: t.head.rotation.z };
}"""

EMP_STATE = """() => ({
  stunT: window.__t.stunT, fires: window.__fires, telegraphs: window.__telegraphs,
  headZ: +window.__t.head.rotation.z.toFixed(3)
})"""

KILL = """() => {
  const t = window.__t; t.hp = 60; t.stunT = 0;
  const dead = t.damage(400, t.pos.clone(), new window.__G.THREE.Vector3(0, 0, 1), 'weak');
  t._update(0.3);
  return { dead, alive: t.alive, visible: t.group.visible, kills: window.__kills, active: t.active };
}"""

AFTER_KILL = """() => {
  const G = window.__G;
  return { active: window.__t.active, inList: G.enemies.list.indexOf(window.__t) >= 0, kills: window.__kills };
}"""

def main():
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--disable-gpu-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(URL, wait_until="load", timeout=120000)
        page.wait_for_function("window.__ready === true", timeout=120000)
        page.wait_for_timeout(800)
        base = page.evaluate("() => ({ready: window.__ready, errors: (window.__errors||[]).slice(0,5), state: window.__G.game.state})")
        print("BASE", json.dumps(base, ensure_ascii=False))
        if not base.get("ready") or base.get("errors"):
            failed.append(f"base not ready/errors: {base}")

        lv = page.evaluate(LEVEL_TURRETS)
        print("LEVEL", json.dumps(lv, ensure_ascii=False))
        if lv.get("pool") != 4:
            failed.append(f"turret pool expected 4, got {lv.get('pool')}")
        if lv.get("alive") != 2:
            failed.append(f"level turrets expected 2, got {lv.get('alive')}")
        if lv.get("errors"):
            failed.append(f"console errors at level: {lv['errors']}")

        setup = page.evaluate(SETUP)
        print("SETUP", json.dumps(setup, ensure_ascii=False))
        if not setup.get("spawned") or setup.get("type") != "turret" or not setup.get("visible"):
            failed.append(f"turret spawn failed: {setup}")
        if setup.get("hp") != 260:
            failed.append(f"turret hp expected 260: {setup}")

        try:
            page.wait_for_function("""() => {
              const G = window.__G, t = window.__t;
              const w = Math.atan2(G.player.pos.x - t.pos.x, G.player.pos.z - t.pos.z);
              let d = t.yaw - w;
              while (d > Math.PI) d -= Math.PI * 2;
              while (d < -Math.PI) d += Math.PI * 2;
              return Math.abs(d) < 0.25;
            }""", timeout=60000)
            tracked = True
        except Exception:
            tracked = False
        tr = page.evaluate(TRACK)
        print("TRACK", json.dumps(tr, ensure_ascii=False))
        if not tracked:
            failed.append(f"turret did not track player: {tr}")

        try:
            page.wait_for_function("() => window.__fires >= 1", timeout=60000)
            fired = True
        except Exception:
            fired = False
        page.wait_for_timeout(2000)
        tr2 = page.evaluate(TRACK)
        print("FIRE", json.dumps(tr2, ensure_ascii=False))
        if not fired or tr2.get("telegraphs", 0) < 1:
            failed.append(f"no turret telegraph/fire: {tr2}")
        dmg_total = 100 - tr2.get("playerHp", 100)
        print("BOLT_DAMAGE", json.dumps({"playerHp": tr2.get("playerHp"), "dealt": dmg_total}))
        if dmg_total <= 0 or abs(dmg_total % 22) > 1e-6:
            failed.append(f"turret bolt damage not 22 per hit: {tr2}")

        page.evaluate("() => { window.__t.cool = 999; window.__t.firing = false; window.__G.player.health = 100; }")

        front = page.evaluate(FRONT)
        print("FRONT", json.dumps(front, ensure_ascii=False))
        if abs(front.get("hp") - 265) > 0.01:
            failed.append(f"front armor expected 265, got {front}")

        back = page.evaluate(BACK)
        print("BACK", json.dumps(back, ensure_ascii=False))
        if abs(back.get("hp") - 200) > 0.01:
            failed.append(f"back damage expected 200, got {back}")

        weak = page.evaluate(WEAK)
        print("WEAK", json.dumps(weak, ensure_ascii=False))
        if abs(weak.get("hp") - 140) > 0.01:
            failed.append(f"weak damage expected 140, got {weak}")

        emp = page.evaluate(EMP)
        print("EMP", json.dumps(emp, ensure_ascii=False))
        if emp.get("affected", 0) < 1 or emp.get("stunT", 0) < 3.5:
            failed.append(f"EMP did not stun turret: {emp}")
        page.wait_for_timeout(2600)
        es = page.evaluate(EMP_STATE)
        print("EMP_STATE", json.dumps(es, ensure_ascii=False))
        if es.get("fires", 0) != 0:
            failed.append(f"turret fired during EMP stun: {es}")
        if es.get("headZ", 0) < 0.05:
            failed.append(f"turret stun visual missing: {es}")

        kill = page.evaluate(KILL)
        print("KILL", json.dumps(kill, ensure_ascii=False))
        if kill.get("alive") or not kill.get("dead") or kill.get("visible"):
            failed.append(f"turret kill handling wrong: {kill}")
        page.wait_for_timeout(600)
        ak = page.evaluate(AFTER_KILL)
        print("AFTER_KILL", json.dumps(ak, ensure_ascii=False))
        if ak.get("inList") or ak.get("active") or ak.get("kills", 0) < 1:
            failed.append(f"turret did not retire: {ak}")

        errs = page.evaluate("() => (window.__errors || []).slice(0, 5)")
        if errs:
            failed.append(f"console errors: {errs}")
        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  phase3b independent browser checks")

if __name__ == "__main__":
    main()
