"""Stage 0 independent browser verification (Playwright + installed Chrome)."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

BASE = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

JS_BASE = """() => ({
  ready: window.__ready,
  fatal: window.__fatal,
  errors: (window.__errors || []).slice(0, 5),
  state: window.__G && window.__G.game && window.__G.game.state,
  mode: window.__G && window.__G.input && window.__G.input.mode,
  locked: !!(window.__G && window.__G.input && window.__G.input.locked),
  pointerLock: !!document.pointerLockElement,
  charges: window.__G && window.__G.gadgets && window.__G.gadgets.charges,
  smokes: window.__G && window.__G.smokes,
  chips: [...document.querySelectorAll('.h-gadget .g-chip')].map(e => e.textContent.trim()),
  chipCount: document.querySelectorAll('.h-gadget .g-chip').length
})"""

JS_RIGHT_DOWN = """() => {
  const c = document.getElementById('view');
  const e = new MouseEvent('mousedown', { button: 2, bubbles: true, cancelable: true, view: window });
  c.dispatchEvent(e);
  return {
    defaultPrevented: e.defaultPrevented,
    downAds: window.__G.input.down('ads'),
    ads: window.__G.input.ads,
    mode: window.__G.input.mode,
    locked: window.__G.input.locked
  };
}"""

JS_STATE = """() => ({
  downAds: window.__G.input.down('ads'),
  ads: window.__G.input.ads,
  mode: window.__G.input.mode,
  locked: window.__G.input.locked,
  pointerLock: !!document.pointerLockElement
})"""

JS_CTX = """() => {
  const c = document.getElementById('view');
  const e = new MouseEvent('contextmenu', { button: 2, bubbles: true, cancelable: true, view: window });
  c.dispatchEvent(e);
  return { defaultPrevented: e.defaultPrevented };
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
        page.goto(BASE, wait_until="load", timeout=120000)
        try:
            page.wait_for_function("window.__ready === true", timeout=120000)
        except Exception as e:
            failed.append(f"ready timeout: {e}")
        page.wait_for_timeout(800)

        base = page.evaluate(JS_BASE)
        print("BASE", json.dumps(base, ensure_ascii=False))
        for key, want in [("ready", True), ("fatal", None)]:
            if base.get(key) != want:
                failed.append(f"{key} expected {want!r}, got {base.get(key)!r}")
        if base.get("errors"):
            failed.append(f"__errors non-empty: {base['errors']}")
        if base.get("chipCount") != 3:
            failed.append(f"h-gadget chips expected 3, got {base.get('chipCount')}")
        if base.get("charges") != {"emp": 2, "smoke": 2, "decoy": 1, "ammo": 1, "stim": 1}:
            failed.append(f"charges mismatch: {base.get('charges')}")
        if base.get("smokes") != []:
            failed.append(f"smokes expected [], got {base.get('smokes')}")

        # Original bug scenario: lock mode, not locked, first right mousedown must set ADS.
        r1 = page.evaluate(JS_RIGHT_DOWN)
        print("RIGHT1", json.dumps(r1, ensure_ascii=False))
        if not r1.get("defaultPrevented"):
            failed.append("first right mousedown not defaultPrevented")
        if not r1.get("downAds"):
            failed.append("first right mousedown did not set ADS (downAds false)")
        page.wait_for_timeout(200)
        after1 = page.evaluate(JS_STATE)
        print("AFTER1", json.dumps(after1, ensure_ascii=False))
        page.mouse.up(button="right")

        ctx = page.evaluate(JS_CTX)
        print("CONTEXTMENU", json.dumps(ctx, ensure_ascii=False))
        if not ctx.get("defaultPrevented"):
            failed.append("contextmenu not defaultPrevented")

        # Selection: 3 -> decoy, 3 again -> ammo, 1 -> emp.
        page.keyboard.press("3")
        page.wait_for_timeout(120)
        sel1 = page.evaluate("() => window.__G.gadgets.selected")
        page.keyboard.press("3")
        page.wait_for_timeout(120)
        sel2 = page.evaluate("() => window.__G.gadgets.selected")
        page.keyboard.press("1")
        page.wait_for_timeout(120)
        sel3 = page.evaluate("() => window.__G.gadgets.selected")
        print("SELECT", json.dumps([sel1, sel2, sel3], ensure_ascii=False))
        if sel1 != "decoy":
            failed.append(f"Digit3 expected decoy, got {sel1}")
        if sel2 != "ammo":
            failed.append(f"second Digit3 expected ammo, got {sel2}")
        if sel3 != "emp":
            failed.append(f"Digit1 expected emp, got {sel3}")

        # Empty shell use via Q: message shown, charge unchanged.
        before = page.evaluate("() => window.__G.gadgets.charges.emp")
        page.keyboard.press("q")
        page.wait_for_timeout(250)
        after = page.evaluate("() => window.__G.gadgets.charges.emp")
        msg = page.evaluate("() => { const m = document.querySelector('.h-msg'); return m ? m.textContent.trim() : ''; }")
        print("USE", json.dumps({"before": before, "after": after, "msg": msg}, ensure_ascii=False))
        if before != after:
            failed.append(f"empty shell use consumed charge: {before} -> {after}")
        if not msg:
            failed.append("empty shell use did not show hud message")

        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  stage0 independent browser checks")

if __name__ == "__main__":
    main()
