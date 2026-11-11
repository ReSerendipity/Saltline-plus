"""Stage 0.5 independent browser verification: stun + smoke LOS + EMP."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

URL = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

SETUP = """() => {
  window.__G.player.enabled = true;
  const V = window.__G.player.pos.constructor;
  const p = new V(-28, 0, 6);
  const en = window.__G.enemies.spawn('hound', p, { state: 'alert', target: window.__G.player.pos });
  window.__target = en;
  window.__fireCount = 0;
  window.__G.events.on('enemy:fire', e => { if (window.__target && e.enemy === window.__target) window.__fireCount++; });
  return {
    spawned: !!en,
    id: en && en.id,
    alive: en && en.alive,
    pos: en && { x: en.pos.x, y: en.pos.y, z: en.pos.z },
    mode: en && en.mode,
    stunT: en && en.stunT
  };
}"""

EMP = """() => {
  window.__fireCount = 0;
  const n = window.__G.combat.emp(window.__G.player.pos, 10, 4);
  return { affected: n, stunT: window.__target && window.__target.stunT, fireCount: window.__fireCount };
}"""

AFTER_EMP = """() => ({
  stunT: window.__target && window.__target.stunT,
  fireCount: window.__fireCount,
  alive: window.__target && window.__target.alive
})"""

SMOKE_ON = """() => {
  const t = window.__target;
  t.stunT = 0;
  t.mode = 'engage';
  t.los = false;
  t.senseT = 0;
  t.noSeeT = 0;
  const a = t.sensor || t.pos;
  const b = window.__G.player.eye || window.__G.player.pos;
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 + 0.9, z: (a.z + b.z) / 2 };
  window.__G.smokes.push({ pos: mid, radius: 6, t: 10 });
  return { smoke: mid, count: window.__G.smokes.length };
}"""

LOS = """() => ({
  los: window.__target && window.__target.los,
  mode: window.__target && window.__target.mode,
  alive: window.__target && window.__target.alive,
  smokes: window.__G.smokes.length
})"""

SMOKE_OFF = """() => { window.__G.smokes.length = 0; return window.__G.smokes.length; }"""

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
        try:
            page.wait_for_function("window.__ready === true", timeout=120000)
        except Exception as e:
            failed.append(f"ready timeout: {e}")
        page.wait_for_timeout(800)
        base = page.evaluate("() => ({ready: window.__ready, errors: (window.__errors||[]).slice(0,5), state: window.__G.game.state, aliveEnemies: window.__G.enemies.aliveCount()})")
        print("BASE", json.dumps(base, ensure_ascii=False))
        if not base.get("ready") or base.get("errors"):
            failed.append(f"base not ready/errors: {base}")

        setup = page.evaluate(SETUP)
        print("SETUP", json.dumps(setup, ensure_ascii=False))
        if not setup.get("spawned") or not setup.get("alive"):
            failed.append(f"enemy spawn failed: {setup}")

        page.wait_for_timeout(300)
        emp = page.evaluate(EMP)
        print("EMP", json.dumps(emp, ensure_ascii=False))
        if emp.get("affected", 0) < 1:
            failed.append(f"EMP affected 0: {emp}")
        if not (emp.get("stunT", 0) > 0):
            failed.append(f"EMP did not set stunT: {emp}")
        page.wait_for_timeout(1500)
        after = page.evaluate(AFTER_EMP)
        print("AFTER_EMP", json.dumps(after, ensure_ascii=False))
        if after.get("fireCount", 0) != 0:
            failed.append(f"stunned enemy fired {after['fireCount']} times")
        if not (after.get("stunT", 0) > 0):
            failed.append(f"stunT expired too early: {after}")

        smoke = page.evaluate(SMOKE_ON)
        print("SMOKE_ON", json.dumps(smoke, ensure_ascii=False))
        page.wait_for_timeout(700)
        los_blocked = page.evaluate(LOS)
        print("LOS_BLOCKED", json.dumps(los_blocked, ensure_ascii=False))
        if los_blocked.get("los") is not False:
            failed.append(f"smoke did not block LOS: {los_blocked}")

        page.evaluate(SMOKE_OFF)
        page.wait_for_timeout(700)
        los_clear = page.evaluate(LOS)
        print("LOS_CLEAR", json.dumps(los_clear, ensure_ascii=False))
        if los_clear.get("los") is not True:
            failed.append(f"LOS did not recover after smoke cleared: {los_clear}")

        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  stage0.5 independent browser checks")

if __name__ == "__main__":
    main()
