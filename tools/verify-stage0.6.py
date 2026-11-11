"""Stage 0.6 independent browser check: ctx.point / ctx.dir / def.update."""
from playwright.sync_api import sync_playwright
import json
import math
import sys
import urllib.parse

URL = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

REGISTER_USE = """() => {
  window.__probe = null;
  window.__updates = 0;
  const S = window.SaltlineGadgets;
  S.register({
    id: 'probe', slot: 0, charges: 1, cooldown: 0, nameKey: 'probe', icon: 'P',
    use: (G, ctx) => { window.__probe = { point: ctx.point, dir: ctx.dir }; return false; },
    update: (G, dt) => { window.__updates++; }
  });
  const g = window.__G.gadgets;
  g.selected = 'probe';
  g.use();
  return { probe: window.__probe, updates: window.__updates };
}"""

READ = """() => ({ probe: window.__probe, updates: window.__updates })"""

def finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)

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

        first = page.evaluate(REGISTER_USE)
        print("FIRST", json.dumps(first, ensure_ascii=False))
        probe = first.get("probe")
        if not probe:
            failed.append("probe use did not run")
        else:
            pt = probe.get("point") or {}
            dr = probe.get("dir") or {}
            if not all(finite(pt.get(k)) for k in ("x", "y", "z")):
                failed.append(f"ctx.point not finite: {pt}")
            length = math.sqrt(sum((dr.get(k) or 0) ** 2 for k in ("x", "y", "z")))
            if abs(length - 1) > 0.01:
                failed.append(f"ctx.dir not unit length: {length}")
        page.wait_for_timeout(400)
        second = page.evaluate(READ)
        print("SECOND", json.dumps(second, ensure_ascii=False))
        if second.get("updates", 0) <= first.get("updates", 0):
            failed.append(f"def.update not called: {first.get('updates')} -> {second.get('updates')}")
        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  stage0.6 independent browser checks")

if __name__ == "__main__":
    main()
