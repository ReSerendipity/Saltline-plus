"""Phase 3C independent verification: secondary weapon (BREACH-12)."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

URL = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

SETUP = """() => {
  const G = window.__G;
  window.__fires = []; window.__swaps = []; window.__errors = window.__errors || [];
  G.events.on('weapon:fire', e => window.__fires.push({ weapon: e.weapon, pellets: e.pellets }));
  G.events.on('weapon:swap', e => window.__swaps.push(e));
  const w = G.weapon;
  return {
    name: w.name, magSize: w.magSize, ammo: w.ammo, reserve: w.reserve, active: w.active,
    damage: w.damage, rpm: w.rpm,
    profiles: w.profiles.map(p => ({ ammo: p.ammo, reserve: p.reserve })),
    errors: (window.__errors || []).slice(0, 5)
  };
}"""

FIRE = """() => {
  window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Enter', key: 'Enter', bubbles: true }));
  return true;
}"""

STOP = """() => {
  window.dispatchEvent(new KeyboardEvent('keyup', { code: 'Enter', key: 'Enter', bubbles: true }));
  return true;
}"""

STATE = """() => {
  const w = window.__G.weapon;
  return {
    name: w.name, ammo: w.ammo, magSize: w.magSize, reserve: w.reserve, active: w.active,
    damage: w.damage, rpm: w.rpm, state: w.state,
    profiles: w.profiles.map(p => ({ ammo: p.ammo, reserve: p.reserve })),
    fires: window.__fires.slice(-6), swaps: window.__swaps.slice(-4),
    hud: (document.body.innerText || '').indexOf('BREACH-12') >= 0,
    errors: (window.__errors || []).slice(0, 5)
  };
}"""

SWITCH = """(i) => {
  const w = window.__G.weapon;
  return { ok: w.switchTo(i), active: w.active, name: w.name, ammo: w.ammo, magSize: w.magSize, reserve: w.reserve };
}"""

RELOAD = """() => {
  const w = window.__G.weapon;
  w.ammo = 0;
  return { ok: w.reloadNow(), state: w.state, reserve: w.reserve };
}"""

TICK = """() => {
  const w = window.__G.weapon;
  for (let i = 0; i < 40; i++) w.update(0.05);
  return { ammo: w.ammo, state: w.state, reserve: w.reserve };
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
        page.wait_for_timeout(1000)
        base = page.evaluate("() => ({ready: window.__ready, errors: (window.__errors||[]).slice(0,5), state: window.__G.game.state})")
        print("BASE", json.dumps(base, ensure_ascii=False))
        if not base.get("ready") or base.get("errors"):
            failed.append(f"base not ready/errors: {base}")

        setup = page.evaluate(SETUP)
        print("SETUP", json.dumps(setup, ensure_ascii=False))
        if setup.get("name") != "PAC-9 Longshore" or setup.get("magSize") != 30 or setup.get("reserve") != 150:
            failed.append(f"initial weapon wrong: {setup}")

        # primary fire
        page.evaluate(FIRE)
        page.wait_for_timeout(900)
        page.evaluate(STOP)
        page.wait_for_timeout(400)
        st = page.evaluate(STATE)
        print("PRIMARY_FIRE", json.dumps({k: st[k] for k in ('ammo','active','fires','errors')}, ensure_ascii=False))
        if st.get("ammo", 30) >= 30:
            failed.append(f"primary did not fire: {st}")
        primary_ammo = st.get("ammo")

        # switch to breach
        sw = page.evaluate(SWITCH, 1)
        print("SWITCH_BREACH", json.dumps(sw, ensure_ascii=False))
        if not sw.get("ok") or sw.get("name") != "BREACH-12" or sw.get("magSize") != 4 or sw.get("ammo") != 4 or sw.get("reserve") != 24:
            failed.append(f"switch to breach wrong: {sw}")

        page.wait_for_timeout(3000)
        page.evaluate(TICK)
        page.evaluate(FIRE)
        page.wait_for_timeout(1200)
        page.evaluate(STOP)
        page.evaluate(TICK)
        st = page.evaluate(STATE)
        print("BREACH_FIRE", json.dumps({k: st[k] for k in ('name','ammo','reserve','active','fires','hud','errors')}, ensure_ascii=False))
        if st.get("ammo", 4) != 3:
            failed.append(f"breach did not consume 1 shell: {st}")
        if not any(f.get("weapon") == "breach" and f.get("pellets") == 6 for f in st.get("fires", [])):
            failed.append(f"breach fire payload wrong: {st.get('fires')}")
        if not st.get("hud"):
            failed.append("HUD missing BREACH-12")

        # reload breach
        rl = page.evaluate(RELOAD)
        print("RELOAD_START", json.dumps(rl, ensure_ascii=False))
        tick = page.evaluate(TICK)
        print("RELOAD_TICK", json.dumps(tick, ensure_ascii=False))
        try:
            page.wait_for_function("() => window.__G.weapon.ammo === 4 && window.__G.weapon.state !== 'reloading'", timeout=30000)
            reloaded = True
        except Exception:
            reloaded = False
        st = page.evaluate(STATE)
        print("RELOAD_END", json.dumps({k: st[k] for k in ('ammo','reserve','state','active','errors')}, ensure_ascii=False))
        if not reloaded or st.get("ammo") != 4 or st.get("reserve") != 20:
            failed.append(f"breach reload wrong: {st}")

        # switch back, ammo pool preserved
        sw = page.evaluate(SWITCH, 0)
        print("SWITCH_PRIMARY", json.dumps(sw, ensure_ascii=False))
        if not sw.get("ok") or sw.get("name") != "PAC-9 Longshore":
            failed.append(f"switch back wrong: {sw}")
        if sw.get("ammo") != primary_ammo:
            failed.append(f"primary ammo pool not preserved: expected {primary_ammo}, got {sw.get('ammo')}")

        st = page.evaluate(STATE)
        print("FINAL", json.dumps({k: st[k] for k in ('name','ammo','reserve','active','hud','swaps','errors')}, ensure_ascii=False))
        if st.get("errors"):
            failed.append(f"console errors: {st['errors']}")
        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  phase3c independent browser checks")

if __name__ == "__main__":
    main()
