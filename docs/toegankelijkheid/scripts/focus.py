from playwright.sync_api import sync_playwright

ACTIVE = """() => {
  let a = document.activeElement;
  while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement;
  if (!a) return null;
  const cs = getComputedStyle(a);
  const vis = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none';
  return { el: a.tagName.toLowerCase(), id: a.id || null,
           tekst: ((a.getAttribute && a.getAttribute('text')) || a.textContent || '').trim().slice(0, 30),
           outline: cs.outlineStyle + ' ' + cs.outlineWidth, shadow: cs.boxShadow.slice(0, 28),
           zichtbaar: vis, hash: location.hash };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
    pg.goto("http://localhost:8080/", wait_until="networkidle")
    pg.wait_for_timeout(1000)
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(200)
    first = pg.evaluate(ACTIVE)
    print("1e tabstop:", first["tekst"], "| zichtbare focus:", first["zichtbaar"])
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(700)
    after = pg.evaluate(ACTIVE)
    print("na Enter  :", after["el"], "id=", after["id"], "hash=", after["hash"])

    pg.goto("http://localhost:8080/", wait_until="networkidle")
    pg.wait_for_timeout(900)
    zonder = 0
    for i in range(10):
        pg.keyboard.press("Tab")
        pg.wait_for_timeout(130)
        r = pg.evaluate(ACTIVE)
        if not r:
            continue
        if not r["zichtbaar"]:
            zonder += 1
        print(f"  {i + 1:2}. {r['el']:10} {r['tekst']!r:34} outline={r['outline']:13} zichtbaar={r['zichtbaar']}")
    print("zonder zichtbare focusindicator:", zonder, "van 10")
    b.close()
