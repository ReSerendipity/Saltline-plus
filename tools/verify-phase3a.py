"""Phase 3A independent verification: shield hound + repair drone."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

URL = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

SETUP = """() => {
  const G = window.__G;
  const base = G.player.pos.clone();
  const hp = new G.THREE.Vector3(base.x + 4, 0, base.z);
  const sh = G.enemies.spawn('hound', hp, { state: 'alert', target: G.player.pos, shield: true });
  const bh = G.enemies.spawn('hound', new G.THREE.Vector3(base.x + 4, 0, base.z + 2), { state: 'alert', target: G.player.pos });
  const sg = G.enemies.spawn('gull', new G.THREE.Vector3(base.x + 6, 4, base.z), { state: 'alert', target: G.player.pos, support: true });
  window.__sh = sh; window.__bh = bh; window.__sg = sg;
  window.__heals = 0; window.__fires = 0;
  G.events.on('enemy:heal', e => { if (e.healer === sg && e.target === bh) window.__heals++; });
  G.events.on('enemy:fire', e => { if (e.enemy === sg) window.__fires++; });
  if (sh) { sh.yaw = 0; sh.hp = sh.hp; }
  return {
    shield: !!sh, shieldFlag: sh && sh.shield, shieldVisible: !!(sh && sh.shieldMesh && sh.shieldMesh.visible),
    support: !!sg, supportFlag: sg && sg.support,
    baseHoundShield: bh && bh.shield,
    patrol: G.game.flow.patrol, waves: G.game.flow.waves
  };
}"""

FRONT = """() => {
  const e = window.__sh; const max = e.hp; const p = e.pos.clone();
  e.damage(100, p, new window.__G.THREE.Vector3(0, 0, -1), 'body');
  return { max, hp: e.hp, part: 'body' };
}"""

BACK = """() => {
  const e = window.__sh; e.hp = 140; const p = e.pos.clone();
  e.damage(100, p, new window.__G.THREE.Vector3(0, 0, 1), 'body');
  return { hp: e.hp };
}"""

WEAK = """() => {
  const e = window.__sh; e.hp = 140; const p = e.pos.clone();
  e.damage(100, p, new window.__G.THREE.Vector3(0, 0, -1), 'weak');
  return { hp: e.hp };
}"""

HEAL = """() => {
  const h = window.__bh; h.hp = 70; window.__heals = 0; window.__fires = 0;
  if (window.__sh) window.__sh.hp = 140; // 让维修机只选择 __bh 作为治疗目标
  return { hp: h.hp, supportHp: window.__sg && window.__sg.hp };
}"""

STATE = """() => ({
  houndHp: window.__bh && window.__bh.hp,
  heals: window.__heals,
  fires: window.__fires,
  supportAtk: window.__sg && window.__sg.atk,
  errors: (window.__errors || []).slice(0, 5)
})"""

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

        setup = page.evaluate(SETUP)
        print("SETUP", json.dumps(setup, ensure_ascii=False))
        if not setup.get("shieldFlag") or not setup.get("shieldVisible"):
            failed.append(f"shield hound not active/visible: {setup}")
        if setup.get("baseHoundShield"):
            failed.append("normal hound has shield flag")
        if not setup.get("supportFlag"):
            failed.append(f"support gull not active: {setup}")
        if not setup.get("patrol", {}).get("shield"):
            failed.append(f"patrol missing shield count: {setup.get('patrol')}")

        front = page.evaluate(FRONT)
        print("FRONT", json.dumps(front, ensure_ascii=False))
        if front.get("hp") != front.get("max") - 15:
            failed.append(f"front shield damage expected 15, got {front}")

        back = page.evaluate(BACK)
        print("BACK", json.dumps(back, ensure_ascii=False))
        if back.get("hp") != 40:
            failed.append(f"back damage expected 40, got {back}")

        weak = page.evaluate(WEAK)
        print("WEAK", json.dumps(weak, ensure_ascii=False))
        if weak.get("hp") != 40:
            failed.append(f"weak damage expected 40, got {weak}")

        heal = page.evaluate(HEAL)
        print("HEAL_SETUP", json.dumps(heal, ensure_ascii=False))
        page.wait_for_timeout(2200)
        st = page.evaluate(STATE)
        print("HEAL_RESULT", json.dumps(st, ensure_ascii=False))
        if st.get("houndHp", 0) <= heal.get("hp", 0):
            failed.append(f"repair drone did not heal: {heal} -> {st.get('houndHp')}")
        if st.get("heals", 0) < 1:
            failed.append(f"no enemy:heal event: {st}")
        if st.get("fires", 0) != 0:
            failed.append(f"support gull fired {st.get('fires')} times")
        if st.get("errors"):
            failed.append(f"console errors: {st['errors']}")
        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  phase3a independent browser checks")

if __name__ == "__main__":
    main()
