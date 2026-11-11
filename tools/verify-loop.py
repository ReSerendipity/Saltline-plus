"""Integrated mission loop check: 3 relays -> allCut -> extraction -> complete."""
from playwright.sync_api import sync_playwright
import json
import sys
import urllib.parse

URL = "http://127.0.0.1:8766/" + urllib.parse.quote("Saltline.html") + "?autostart=1"

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

        cut = page.evaluate("""() => {
          window.__G.player.invulnerable = true;
          window.__G.game.debugCut();
          window.__G.game.debugCut();
          window.__G.game.debugCut();
          return {
            cut: window.__G.game.run.cut,
            allCut: window.__G.game.run.allCut,
            objective: document.querySelector('.h-obj-t').textContent.trim(),
            relays: document.querySelector('.h-relays b').textContent.trim()
          };
        }""")
        print("CUT", json.dumps(cut, ensure_ascii=False))
        if cut.get("cut") != 3 or not cut.get("allCut"):
            failed.append(f"relay cut/allCut mismatch: {cut}")
        if cut.get("relays") != "3/3":
            failed.append(f"relay HUD mismatch: {cut.get('relays')}")

        tele = page.evaluate("""() => {
          const G = window.__G;
          G.player.pos.copy(G.level.extraction.pos);
          G.player.vel.set(0, 0, 0);
          return { x: G.player.pos.x, y: G.player.pos.y, z: G.player.pos.z };
        }""")
        print("TELEPORT", json.dumps(tele, ensure_ascii=False))
        page.wait_for_timeout(1200)
        done = page.evaluate("() => ({ state: window.__G.game.state, screen: document.querySelector('.menu').dataset.screen, errors: (window.__errors||[]).slice(0,5) })")
        print("DONE", json.dumps(done, ensure_ascii=False))
        if done.get("state") != "complete":
            failed.append(f"state not complete: {done}")
        if done.get("errors"):
            failed.append(f"errors: {done['errors']}")
        browser.close()

    if failed:
        print("FAIL")
        for f in failed:
            print(" -", f)
        sys.exit(1)
    print("PASS  integrated mission loop check")

if __name__ == "__main__":
    main()
