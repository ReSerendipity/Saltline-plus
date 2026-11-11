"""Stage 1 integrated verification: EMP, smoke, decoy/ammo/stim."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

URL = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

BASE = """() => ({
  ready: window.__ready,
  errors: (window.__errors || []).slice(0, 6),
  state: window.__G.game.state,
  chips: [...document.querySelectorAll('.h-gadget .g-chip')].map(e => e.textContent.trim()),
  charges: window.__G.gadgets.charges
})"""

SPAWN = """() => {
  const G = window.__G;
  const d = new G.THREE.Vector3();
  G.camera.getWorldDirection(d);
  const eye = G.camera.position.clone();
  const hit = G.physics.raycast(eye, d, 20);
  const aim = hit && hit.point ? hit.point : eye.clone().addScaledVector(d, 20);
  // 站在瞄准点前 2m，确保落在 EMP 8m / 烟幕 4m / 诱饵 14m 范围内
  const p = aim.clone().addScaledVector(d, -2);
  p.y = 0;
  const e = G.enemies.spawn('hound', p, { state: 'alert', target: G.player.pos });
  window.__target = e;
  window.__aim = { x: aim.x, y: aim.y, z: aim.z };
  return e ? { id: e.id, alive: e.alive, pos: { x: e.pos.x, y: e.pos.y, z: e.pos.z }, aim: window.__aim, mode: e.mode } : null;
}"""

STATE = """() => ({
  charges: window.__G.gadgets.charges,
  selected: window.__G.gadgets.selected,
  smokes: window.__G.smokes.length,
  stunT: window.__target && window.__target.stunT,
  enemyMode: window.__target && window.__target.mode,
  los: window.__target && window.__target.los,
  reserve: window.__G.weapon.reserve,
  health: window.__G.player.health
})"""

SMOKE_BLOCK = """() => {
  const t = window.__target;
  t.stunT = 0; t.mode = 'engage'; t.los = false; t.senseT = 0; t.noSeeT = 0;
  const a = t.sensor || t.pos;
  const b = window.__G.player.eye || window.__G.player.pos;
  window.__G.smokes.push({ pos: { x: (a.x+b.x)/2, y: (a.y+b.y)/2 + .9, z: (a.z+b.z)/2 }, radius: 6, t: 10, puffT: 0 });
  return window.__G.smokes.length;
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
        base = page.evaluate(BASE)
        print("BASE", json.dumps(base, ensure_ascii=False))
        if not base.get("ready") or base.get("errors"):
            failed.append(f"base not ready/errors: {base}")
        if base.get("charges") != {"emp": 2, "smoke": 2, "decoy": 1, "ammo": 1, "stim": 1}:
            failed.append(f"charges mismatch: {base.get('charges')}")

        spawned = page.evaluate(SPAWN)
        print("SPAWN", json.dumps(spawned, ensure_ascii=False))
        if not spawned or not spawned.get("alive"):
            failed.append(f"enemy spawn failed: {spawned}")

        # EMP
        page.keyboard.press("1")
        page.wait_for_timeout(100)
        page.keyboard.press("q")
        page.wait_for_timeout(250)
        st = page.evaluate(STATE)
        print("EMP", json.dumps(st, ensure_ascii=False))
        if not (st.get("stunT", 0) > 0):
            failed.append(f"EMP stunT not set: {st}")
        if st.get("charges", {}).get("emp") != 1:
            failed.append(f"EMP charge not consumed: {st.get('charges')}")
        if st.get("selected") != "emp":
            failed.append(f"selected expected emp: {st.get('selected')}")

        # Smoke
        page.keyboard.press("2")
        page.wait_for_timeout(100)
        page.keyboard.press("q")
        page.wait_for_timeout(300)
        st = page.evaluate(STATE)
        print("SMOKE", json.dumps(st, ensure_ascii=False))
        if st.get("smokes", 0) < 1:
            failed.append(f"smoke not deployed: {st}")
        if st.get("charges", {}).get("smoke") != 1:
            failed.append(f"smoke charge not consumed: {st.get('charges')}")

        # Smoke LOS block
        page.evaluate(SMOKE_BLOCK)
        page.wait_for_timeout(700)
        st = page.evaluate(STATE)
        print("LOS_BLOCKED", json.dumps(st, ensure_ascii=False))
        if st.get("los") is not False:
            failed.append(f"smoke did not block LOS: {st}")
        page.evaluate("() => { window.__G.smokes.length = 0; window.__target.stunT = 0; }")
        page.wait_for_timeout(700)
        st = page.evaluate(STATE)
        print("LOS_CLEAR", json.dumps(st, ensure_ascii=False))
        if st.get("los") is not True:
            failed.append(f"LOS did not recover: {st}")

        # Support: decoy -> ammo -> stim
        page.evaluate("() => { window.__target.mode = 'patrol'; window.__target.stunT = 0; }")
        page.keyboard.press("3")
        page.wait_for_timeout(100)
        page.keyboard.press("q")
        page.wait_for_timeout(1200)
        st = page.evaluate(STATE)
        print("DECOY", json.dumps(st, ensure_ascii=False))
        if st.get("charges", {}).get("decoy") != 0:
            failed.append(f"decoy charge not consumed: {st.get('charges')}")
        if st.get("enemyMode") == "patrol":
            failed.append(f"decoy did not alert enemy: {st}")

        page.keyboard.press("3")
        page.wait_for_timeout(100)
        before_reserve = page.evaluate("() => window.__G.weapon.reserve")
        page.keyboard.press("q")
        page.wait_for_timeout(250)
        st = page.evaluate(STATE)
        print("AMMO", json.dumps(st, ensure_ascii=False))
        if st.get("reserve", 0) < before_reserve + 60:
            failed.append(f"ammo not added: {before_reserve} -> {st.get('reserve')}")

        page.keyboard.press("3")
        page.wait_for_timeout(100)
        page.evaluate("() => { window.__G.player.health = 40; }")
        page.keyboard.press("q")
        page.wait_for_timeout(250)
        st = page.evaluate(STATE)
        print("STIM", json.dumps(st, ensure_ascii=False))
        if st.get("health", 0) < 85:
            failed.append(f"stim did not heal: {st.get('health')}")

        final = page.evaluate("() => ({ errors: (window.__errors || []).slice(0, 6), charges: window.__G.gadgets.charges })")
        print("FINAL", json.dumps(final, ensure_ascii=False))
        if final.get("errors"):
            failed.append(f"console errors: {final['errors']}")
        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  stage1 integrated browser checks")

if __name__ == "__main__":
    main()
