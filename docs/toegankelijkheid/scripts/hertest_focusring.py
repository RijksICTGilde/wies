"""Focusring per tabstop, gemeten als pixelverschil.

Een berekende `outline` zegt niets: het design system tekent de ring in een
shadow root en :focus-visible zit niet in getComputedStyle. Wat wel telt is of
het scherm verandert als de focus verschuift. Per tabstop: screenshot van het
gefocuste element met en zonder focus, en het aantal afwijkende pixels.

In Firefox werkt dit niet: de ring wordt na blur() niet binnen de meettijd
hertekend, zodat elk verschil 0 is. Gebruik daar een screenshot.

Gebruik: python3 hertest_focusring.py <sessionid> [chromium|edge|firefox]
"""
from playwright.sync_api import sync_playwright
import sys, json
from PIL import Image, ImageChops
import io

SID = sys.argv[1] if len(sys.argv) > 1 else ""
PAGES = ["/", "/opdrachten/", "/beheer/gebruikers/", "/profiel/"]
STOPS = 14

JS_BOX = """() => {
  let a = document.activeElement; if (!a || a === document.body) return null;
  const r = a.getBoundingClientRect();
  if (!r.width || !r.height) return null;
  return {x: Math.max(0, r.x-6), y: Math.max(0, r.y-6), w: r.width+12, h: r.height+12,
          tag: a.tagName, label: (a.getAttribute('aria-label')||a.textContent||'').trim().slice(0,28)};
}"""

def engines(p):
    yield "Chromium", lambda: p.chromium.launch()
    yield "Edge", lambda: p.chromium.launch(channel="msedge")
    yield "Firefox", lambda: p.firefox.launch()

def diff_pixels(a, b):
    ia, ib = Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB")
    if ia.size != ib.size: return -1
    d = ImageChops.difference(ia, ib).convert("L")
    return sum(1 for px in d.getdata() if px > 24)

def run(only=None):
    out = {}
    with sync_playwright() as p:
        for name, launch in engines(p):
            if only and only.lower() not in name.lower(): continue
            try: b = launch()
            except Exception as e: out[name] = {"error": str(e).splitlines()[0][:60]}; continue
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            ctx.add_cookies([{"name": "sessionid", "value": SID, "domain": "localhost", "path": "/"}])
            page = ctx.new_page()
            res = {}
            for url in PAGES:
                page.goto("http://localhost:8080" + url, wait_until="load", timeout=20000)
                page.wait_for_timeout(800)
                zonder = []
                for i in range(STOPS):
                    page.keyboard.press("Tab")
                    box = page.evaluate(JS_BOX)
                    if not box: break
                    clip = {"x": box["x"], "y": box["y"], "width": box["w"], "height": box["h"]}
                    met = page.screenshot(clip=clip)
                    # Focus even wegnemen zonder de tabvolgorde te verstoren.
                    page.evaluate("() => document.activeElement.blur()")
                    page.wait_for_timeout(60)
                    los = page.screenshot(clip=clip)
                    # Focus terugzetten op hetzelfde element.
                    page.evaluate("() => { const el=[...document.querySelectorAll('*')].find(e=>e.matches(':focus-visible')); }")
                    n = diff_pixels(met, los)
                    if n == 0: zonder.append(f"{box['tag']} {box['label']!r}")
                    # Herstel focus voor de volgende Tab door Shift+Tab en Tab.
                    page.keyboard.press("Shift+Tab"); page.keyboard.press("Tab")
                res[url] = {"tabstops": i + 1 if box else i, "zonder_ring": zonder}
            b.close(); out[name] = res
    return out

if __name__ == "__main__":
    only = sys.argv[2] if len(sys.argv) > 2 else None
    r = run(only)
    prev = {}
    try: prev = json.load(open("focusring.json"))
    except Exception: pass
    prev.update(r); json.dump(prev, open("focusring.json", "w"), indent=1)
    for eng, res in r.items():
        print(f"=== {eng} ===")
        if "error" in res: print("  ", res["error"]); continue
        for url, d in res.items():
            print(f"  {url:36} stops={d['tabstops']:2} zonder ring={len(d['zonder_ring'])}", ("  " + "; ".join(d["zonder_ring"][:3])) if d["zonder_ring"] else "")
